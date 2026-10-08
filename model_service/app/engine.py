"""vLLM-backed safety engine for ShieldGemma generative classification.

Two engine paths coexist behind the ``VLLM_USE_ASYNC_ENGINE`` env flag:

* ``AsyncLLMEngine`` (default, ``VLLM_USE_ASYNC_ENGINE=true``) — vLLM's
  online-serving engine. A single background loop owns the ZMQ IPC to the
  ``EngineCore`` subprocess; callers submit per-request IDs through an
  asyncio queue, and vLLM's continuous-batching scheduler interleaves them
  into a single GPU step. This is the architecturally correct path for
  serving concurrent HTTP requests and fixes crash modes where concurrent
  ``asyncio.to_thread(LLM.generate)`` calls race on IPC framing and wedge
  the subprocess. ``CancelledError`` on a caller triggers ``engine.abort(request_id)``
  so timed-out or cancelled requests do not leak GPU resources.

* ``LLM`` (``VLLM_USE_ASYNC_ENGINE=false``) — the offline/batch API.
  Retained as a rollback option if the async path regresses in a specific
  environment. Guarded by an asyncio lock to serialize batch calls.

* ``LocalSafetyEngine`` — PyTorch Hugging Face scoring-mode engine.
  Retained as a CPU/local-dev fallback when vLLM is unavailable or uninstalled.

Configuration knobs (all read at engine construction):

* ``VLLM_USE_ASYNC_ENGINE`` — engine path selector. Default ``true``.
* ``VLLM_MAX_NUM_SEQS`` — continuous-batching cap for the async path. Default 64.
* ``VLLM_ENABLE_PREFIX_CACHING`` — toggle prefix caching on the async path. Default ``true``.
* ``VLLM_ENFORCE_EAGER`` — enforce eager PyTorch execution instead of CUDA graph capture. Default ``true``.
* ``VLLM_GPU_MEMORY_UTILIZATION`` — fraction of GPU memory for vLLM. Default ``0.9``.
* ``VLLM_LOGPROBS`` — top-k logprobs returned per token. Default ``20``.
* ``VLLM_MAX_TOKENS`` — max new tokens to generate. Default ``1`` (classification mode).
* ``USE_VLLM`` — toggle vLLM vs LocalSafetyEngine. Default ``true``.
"""

from __future__ import annotations

import asyncio
import dataclasses
import inspect
import math
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Optional, Union

from loguru import logger

try:
    import torch
except ImportError:
    torch = None

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
except ImportError:
    AutoModelForCausalLM = None  # type: ignore[assignment]
    AutoTokenizer = None  # type: ignore[assignment]

try:
    from vllm import (
        LLM,
        AsyncEngineArgs,
        AsyncLLMEngine,
        SamplingParams,
    )
    from vllm.outputs import RequestOutput

    VLLM_AVAILABLE = True
except ImportError:
    LLM = None
    AsyncEngineArgs = None
    AsyncLLMEngine = None

    class SamplingParams:  # type: ignore[no-redef]
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    class RequestOutput:  # type: ignore[no-redef]
        pass

    VLLM_AVAILABLE = False
    logger.warning("vllm not installed — generative safety models will use LocalSafetyEngine fallback if available")

from model_service.app.config import settings
from model_service.app.engines.tokenizer_pool import (
    TokenizerPool,
    configured_pool_size,
)

# Gemma/SentencePiece representations: include standard, underline (\u2581), lowercase, and capitalized
_YES_VARIANTS = (
    "Yes", "▁Yes", "yes", "▁yes", "YES", "▁YES",
    " Yes", " yes", " YES",
    "\u2581Yes", "\u2581yes", "\u2581YES",
    "\nYes", "\nyes", "\nYES",
)
_NO_VARIANTS = (
    "No", "▁No", "no", "▁no", "NO", "▁NO",
    " No", " no", " NO",
    "\u2581No", "\u2581no", "\u2581NO",
    "\nNo", "\nno", "\nNO",
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Invalid int for {}={!r}; using default {}", name, raw, default)
        return default


def _filter_dataclass_kwargs(cls: Any, kwargs: dict[str, Any]) -> dict[str, Any]:
    """Filter kwargs to only those accepted by a dataclass, for version compatibility."""
    if dataclasses.is_dataclass(cls):
        valid = {f.name for f in dataclasses.fields(cls)}
        return {k: v for k, v in kwargs.items() if k in valid}
    return kwargs


class VLLMSafetyEngine:
    """Wraps vLLM for ShieldGemma generative safety classification.

    Accepts a batch of category prompts, runs them through vLLM's
    continuous-batching generate, and extracts Yes/No logprobs from
    the first generated token to compute violation probabilities.
    """

    def __init__(
        self,
        model_id: str,
        model_path: Optional[str] = None,
        quantization: Optional[str] = None,
    ):
        if not VLLM_AVAILABLE:
            raise RuntimeError(
                "vllm is not installed. Install vllm or configure USE_VLLM=false to use LocalSafetyEngine."
            )

        resolved_path = model_path or str(settings.get_model_path(model_id))
        self._use_async = _env_bool("VLLM_USE_ASYNC_ENGINE", True)
        self.device = "cuda" if (torch is not None and torch.cuda.is_available()) else getattr(settings, "compute_device", "cuda")

        logger.info(
            "Loading vLLM model {} from {} (quantization={}, use_async_engine={})",
            model_id, resolved_path, quantization, self._use_async,
        )

        self.model_id = model_id
        self.model_path = resolved_path

        # HF fast tokenizers are not re-entrant. vLLM uses one internally for
        # generation; for our pre-inference length checks we prefer a
        # dedicated pool of lightweight tokenizer copies so the length check
        # never blocks on vLLM's own tokenizer. ``tokenizer_lock`` remains as
        # a single-tokenizer fallback.
        self.tokenizer_lock: asyncio.Lock = asyncio.Lock()
        self._sync_lock: asyncio.Lock = asyncio.Lock()

        if AutoTokenizer is None:
            raise RuntimeError(
                "transformers.AutoTokenizer is required to build VLLMSafetyEngine "
                "but is not importable."
            )
        self._init_tokenizer = AutoTokenizer.from_pretrained(resolved_path)

        self.llm: Optional[LLM] = None
        self.async_engine: Optional[AsyncLLMEngine] = None

        gpu_util = getattr(settings, "vllm_gpu_memory_utilization", 0.9)
        max_model_len = getattr(settings, "max_model_len", settings.max_input_tokens)

        if self._use_async:
            engine_args_candidates = {
                "model": resolved_path,
                "quantization": quantization,
                "dtype": "auto",
                "gpu_memory_utilization": gpu_util,
                "max_model_len": max_model_len,
                "enforce_eager": _env_bool("VLLM_ENFORCE_EAGER", True),
                "max_num_seqs": _env_int("VLLM_MAX_NUM_SEQS", 64),
                "enable_prefix_caching": _env_bool("VLLM_ENABLE_PREFIX_CACHING", True),
                "trust_remote_code": True,
            }
            filtered_args = _filter_dataclass_kwargs(AsyncEngineArgs, engine_args_candidates)
            engine_args = AsyncEngineArgs(**filtered_args)
            self.async_engine = AsyncLLMEngine.from_engine_args(engine_args)
        else:
            llm_args_candidates = {
                "model": resolved_path,
                "quantization": quantization,
                "dtype": "auto",
                "gpu_memory_utilization": gpu_util,
                "max_model_len": max_model_len,
                "enforce_eager": _env_bool("VLLM_ENFORCE_EAGER", True),
                "trust_remote_code": True,
            }
            filtered_args = _filter_dataclass_kwargs(LLM, llm_args_candidates)
            self.llm = LLM(**filtered_args)

        try:
            pool_size = max(configured_pool_size(), 2)
            self.tokenizer_pool: Optional[TokenizerPool] = TokenizerPool.build(
                resolved_path, size=pool_size
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "Failed to build tokenizer pool for {}; length checks will use our init tokenizer under a lock",
                model_id,
            )
            self.tokenizer_pool = None

        vocab = self._init_tokenizer.get_vocab()

        self.yes_token_ids: set[int] = set()
        self.no_token_ids: set[int] = set()

        for variant in _YES_VARIANTS:
            tid = vocab.get(variant)
            if tid is not None:
                self.yes_token_ids.add(tid)
        for variant in _NO_VARIANTS:
            tid = vocab.get(variant)
            if tid is not None:
                self.no_token_ids.add(tid)

        # Also inspect single-word tokenization outputs without special tokens
        for word in ("Yes", "No", " Yes", " No", " yes", " no", " YES", " NO"):
            ids = self._init_tokenizer.encode(word, add_special_tokens=False)
            if len(ids) == 1:
                clean = word.strip().lower()
                if clean == "yes":
                    self.yes_token_ids.add(ids[0])
                elif clean == "no":
                    self.no_token_ids.add(ids[0])

        if not self.yes_token_ids or not self.no_token_ids:
            raise ValueError(
                f"Tokenizer for {model_id} has no recognisable Yes/No tokens. "
                f"Checked variants: {_YES_VARIANTS + _NO_VARIANTS}. "
                f"Sample vocab keys starting with Y/N: "
                f"{[k for k in vocab if k.startswith(('Y', 'y'))][:10]}, "
                f"{[k for k in vocab if k.startswith(('N', 'n'))][:10]}"
            )

        logger.info(
            "vLLM engine ready for {} — path={}, yes_token_ids={}, no_token_ids={}",
            model_id,
            "async" if self._use_async else "sync",
            self.yes_token_ids,
            self.no_token_ids,
        )

    def _resolved_max_input_tokens(self) -> int | None:
        """Return the per-engine max input token cap, or None when unset."""
        if hasattr(settings, "get_registry_entry"):
            entry = settings.get_registry_entry(self.model_id)
            if entry is not None and getattr(entry, "max_input_tokens", None) is not None:
                return entry.max_input_tokens
        return getattr(settings, "max_input_tokens", 4096)

    def _get_tokenizer(self):
        """Return a tokenizer usable for .encode() / .get_vocab()."""
        return self._init_tokenizer

    def _is_yes(self, token_id: int, decoded: Optional[str]) -> bool:
        if token_id in self.yes_token_ids:
            return True
        if decoded is not None:
            clean = decoded.strip().lower()
            if clean == "yes" or clean.startswith("yes"):
                return True
        return False

    def _is_no(self, token_id: int, decoded: Optional[str]) -> bool:
        if token_id in self.no_token_ids:
            return True
        if decoded is not None:
            clean = decoded.strip().lower()
            if clean == "no" or clean.startswith("no"):
                return True
        return False

    async def _generate_sync_locked(self, texts: list[str], sampling_params: Any) -> list[RequestOutput]:
        """Legacy batch-API path serialized behind a lock to avoid worker races."""
        assert self.llm is not None, "_generate_sync called without an LLM instance"
        async with self._sync_lock:
            return await asyncio.to_thread(self.llm.generate, texts, sampling_params)

    async def _generate_one(self, text: str, sampling_params: Any) -> RequestOutput:
        """Async single-prompt generate with cooperative cancellation."""
        assert self.async_engine is not None, "_generate_one called without async_engine"
        request_id = f"sg-{uuid.uuid4().hex}"
        final: Optional[RequestOutput] = None
        try:
            async for output in self.async_engine.generate(text, sampling_params, request_id):
                final = output
        except asyncio.CancelledError:
            try:
                maybe_coro = self.async_engine.abort(request_id)
                if inspect.isawaitable(maybe_coro):
                    await maybe_coro
            except Exception:  # noqa: BLE001
                logger.exception(
                    "vLLM abort failed for request_id={} on {}",
                    request_id, self.model_id,
                )
            raise
        if final is None:
            raise RuntimeError(
                f"vLLM async_engine.generate yielded no output for request_id={request_id}"
            )
        return final

    async def count_tokens(self, texts: list[str]) -> list[int]:
        """Return the token count for each input using a pooled tokenizer."""
        if self.tokenizer_pool is not None:
            async with self.tokenizer_pool.checkout() as tok:
                return await asyncio.to_thread(lambda: [len(tok.encode(t)) for t in texts])

        tokenizer = self._get_tokenizer()
        async with self.tokenizer_lock:
            return await asyncio.to_thread(lambda: [len(tokenizer.encode(t)) for t in texts])

    def _extract_yes_no_probs(
        self, logprobs_dict: dict, raw_text: str, category: str, top_k: int,
    ) -> tuple[float, float]:
        """Extract yes/no probabilities from logprobs with multi-variant matching and text fallback."""
        exp_yes = 0.0
        exp_no = 0.0

        for raw_token_id, logprob_obj in logprobs_dict.items():
            try:
                token_id = int(raw_token_id)
            except (ValueError, TypeError):
                token_id = raw_token_id  # type: ignore[assignment]

            lp_val = getattr(logprob_obj, "logprob", logprob_obj)
            if not isinstance(lp_val, (int, float)):
                continue

            decoded = getattr(logprob_obj, "decoded_token", None)

            if self._is_yes(token_id, decoded):
                exp_yes += math.exp(lp_val)
            elif self._is_no(token_id, decoded):
                exp_no += math.exp(lp_val)

        total = exp_yes + exp_no
        if total > 0.0:
            yes_prob = exp_yes / total
            return round(yes_prob, 4), round(1.0 - yes_prob, 4)

        top_tokens = []
        for lp in logprobs_dict.values():
            dec = getattr(lp, "decoded_token", str(lp))
            val = getattr(lp, "logprob", lp)
            if isinstance(val, (int, float)):
                top_tokens.append((dec, round(val, 4)))
        top_tokens.sort(key=lambda x: x[1], reverse=True)

        logger.warning(
            "No Yes/No token variant found in top-{} logprobs for '{}'. "
            "Raw text='{}'. Top tokens: {}",
            top_k, category, raw_text, top_tokens[:5],
        )

        lower = raw_text.strip().lower()
        if lower.startswith("yes"):
            return 1.0, 0.0
        if lower.startswith("no"):
            return 0.0, 1.0

        logger.warning(
            "Raw text fallback also inconclusive for '{}' (text='{}'). "
            "Returning uncertain result (yes_prob=0.5).",
            category, raw_text,
        )
        return 0.5, 0.5

    async def analyze_batch(self, prompts: list[dict], max_new_tokens: int = 128) -> list[dict]:
        """Run all category prompts as a single vLLM batch.

        Args:
            prompts: List of dicts with keys ``category`` and ``text``.
            max_new_tokens: Max new tokens to generate per prompt.

        Returns:
            List of dicts with ``category``, ``yes_prob``, ``no_prob``, ``raw_text``.
        """
        texts = [p["text"] for p in prompts]

        # Length-check using a pooled tokenizer slot
        max_input_tokens = self._resolved_max_input_tokens()
        if max_input_tokens is not None:
            token_counts = await self.count_tokens(texts)
            for prompt, token_count in zip(prompts, token_counts):
                if token_count > max_input_tokens:
                    category = prompt.get("category", "<unknown>")
                    raise ValueError(
                        f"Prompt for '{category}' is {token_count} tokens, "
                        f"exceeding the {max_input_tokens}-token limit "
                        f"for {self.model_id}."
                    )

        # Classification mode inspects first token logprobs
        max_gen_tokens = _env_int("VLLM_MAX_TOKENS", 1)
        logprobs_k = _env_int("VLLM_LOGPROBS", 20)

        sampling_params = SamplingParams(
            max_tokens=max_gen_tokens,
            logprobs=logprobs_k,
            temperature=0.0,
        )

        if self._use_async:
            outputs = await asyncio.gather(
                *(self._generate_one(t, sampling_params) for t in texts)
            )
        else:
            outputs = await self._generate_sync_locked(texts, sampling_params)

        results = []
        for prompt_meta, output in zip(prompts, outputs):
            category = prompt_meta["category"]
            first_output = output.outputs[0] if (output.outputs and len(output.outputs) > 0) else None
            raw_text = first_output.text.strip() if first_output else ""

            first_token_logprobs = None
            if first_output and first_output.logprobs and len(first_output.logprobs) > 0:
                first_token_logprobs = first_output.logprobs[0]

            if first_token_logprobs is None:
                logger.error(
                    "No logprobs returned for category '{}'. "
                    "Model may have produced empty output.",
                    category,
                )
                results.append({
                    "category": category,
                    "yes_prob": 0.5,
                    "no_prob": 0.5,
                    "raw_text": raw_text or "Uncertain",
                })
                continue

            yes_prob, no_prob = self._extract_yes_no_probs(
                first_token_logprobs, raw_text, category, sampling_params.logprobs,
            )

            results.append({
                "category": category,
                "yes_prob": yes_prob,
                "no_prob": no_prob,
                "raw_text": raw_text or ("Yes" if yes_prob >= 0.5 else "No"),
            })

        return results

    async def close(self) -> None:
        """Gracefully release engine resources and background tasks."""
        logger.info("Closing VLLMSafetyEngine for {}", self.model_id)


class LocalSafetyEngine:
    """ShieldGemma safety classification using scoring mode (single forward pass).

    Extracts Yes/No probabilities from the last token position to determine
    whether content violates a given safety policy.
    """

    def __init__(self, model_id: str, model_path: Optional[str] = None):
        if torch is None or AutoTokenizer is None or AutoModelForCausalLM is None:
            raise RuntimeError(
                "torch and transformers are required to initialize LocalSafetyEngine."
            )

        self.device = getattr(settings, "compute_device", "cpu")
        self.model_id = model_id
        self.max_input_tokens = getattr(settings, "max_input_tokens", 4096)

        resolved_path = model_path or str(settings.get_model_path(model_id))
        logger.info("Loading {} from {} on device={}", model_id, resolved_path, self.device)

        # On network/FUSE filesystems (like GCS FUSE), safetensors random mmap causes
        # severe page-fault latency and stalls. Stage files to local /tmp with sequential
        # reads first to load in seconds, then prune safetensors to reclaim RAM.
        source_dir = Path(resolved_path)
        load_dir = source_dir
        staged_safetensors: list[Path] = []

        if source_dir.is_dir() and not str(source_dir).startswith("/tmp"):
            tmp_stage = Path("/tmp") / source_dir.name
            tmp_stage.mkdir(parents=True, exist_ok=True)
            logger.info("Staging model files from {} to {} for fast local I/O...", source_dir, tmp_stage)
            for item in source_dir.iterdir():
                if item.is_file():
                    target_file = tmp_stage / item.name
                    if not target_file.exists() or target_file.stat().st_size != item.stat().st_size:
                        logger.info("Staging {} ({:.1f} MB)...", item.name, item.stat().st_size / (1024 * 1024))
                        with open(item, "rb") as src, open(target_file, "wb") as dst:
                            shutil.copyfileobj(src, dst, length=16 * 1024 * 1024)
                    if item.suffix == ".safetensors":
                        staged_safetensors.append(target_file)
            load_dir = tmp_stage
            logger.info("Model staging to {} complete", tmp_stage)

        # MPS/CPU need float32 to avoid NaN; CUDA can use bfloat16
        torch_dtype = torch.float32 if self.device in ("mps", "cpu") else torch.bfloat16

        self.tokenizer = AutoTokenizer.from_pretrained(str(load_dir))
        self.model = AutoModelForCausalLM.from_pretrained(
            str(load_dir),
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        ).to(self.device)
        self.model.eval()

        # Clean up staged safetensors from /tmp (tmpfs) to immediately reclaim RAM
        for sf in staged_safetensors:
            try:
                sf.unlink(missing_ok=True)
                logger.info("Reclaimed tmpfs memory by removing staged {}", sf.name)
            except Exception as e:
                logger.warning("Could not remove staged file {}: {}", sf, e)

        vocab = self.tokenizer.get_vocab()
        self.yes_token_id = vocab.get("Yes")
        self.no_token_id = vocab.get("No")

        if self.yes_token_id is None or self.no_token_id is None:
            raise ValueError(f"Tokenizer for {model_id} missing 'Yes'/'No' tokens.")

        logger.info(
            "Engine ready for {} — Yes token={}, No token={}",
            model_id, self.yes_token_id, self.no_token_id,
        )

    def _score_sync(self, texts: list[str]) -> list[dict]:
        results = []
        for text in texts:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                truncation=True,
                max_length=self.max_input_tokens,
            ).to(self.device)

            with torch.no_grad():
                logits = self.model(**inputs).logits

            last_logits = logits[0, -1, :]
            selected_logits = last_logits[[self.yes_token_id, self.no_token_id]]
            probs = torch.softmax(selected_logits.float(), dim=-1)

            if torch.isnan(probs).any():
                logger.warning("NaN probabilities for {}, defaulting to 0.0", self.model_id)
                yes_prob = 0.0
            else:
                yes_prob = probs[0].item()

            results.append({
                "yes_prob": round(yes_prob, 4),
                "no_prob": round(1 - yes_prob, 4),
                "raw_text": "Yes" if yes_prob >= 0.5 else "No",
            })
        return results

    async def analyze_batch(self, prompts: list[dict], max_new_tokens: int = 128) -> list[dict]:
        texts = [p["text"] for p in prompts]
        outputs = await asyncio.to_thread(self._score_sync, texts)
        return [
            {"category": prompt["category"], **result}
            for prompt, result in zip(prompts, outputs)
        ]

    async def close(self) -> None:
        """No-op cleanup for LocalSafetyEngine."""
        pass


def get_safety_engine(
    model_id: str,
    model_path: Optional[str] = None,
    quantization: Optional[str] = None,
) -> Union[VLLMSafetyEngine, LocalSafetyEngine]:
    """Factory to instantiate the appropriate safety engine.

    Prefers VLLMSafetyEngine when vLLM is available and settings.use_vllm is True;
    falls back to LocalSafetyEngine when vLLM is not installed or when running on
    environments without vLLM support (e.g. CPU local development).
    """
    if VLLM_AVAILABLE and getattr(settings, "use_vllm", True):
        try:
            logger.info("Instantiating VLLMSafetyEngine for {}", model_id)
            return VLLMSafetyEngine(model_id=model_id, model_path=model_path, quantization=quantization)
        except Exception:
            logger.exception("Failed to initialize VLLMSafetyEngine for {}; falling back to LocalSafetyEngine", model_id)

    logger.info("Instantiating LocalSafetyEngine for {}", model_id)
    return LocalSafetyEngine(model_id=model_id, model_path=model_path)
