import asyncio

import torch
from loguru import logger
from transformers import AutoTokenizer, AutoModelForCausalLM

from model_service.app.config import settings


class LocalSafetyEngine:
    """ShieldGemma safety classification using scoring mode (single forward pass).

    Extracts Yes/No probabilities from the last token position to determine
    whether content violates a given safety policy.
    """

    def __init__(self, model_id: str, model_path: str):
        self.device = settings.compute_device
        self.model_id = model_id
        self.max_input_tokens = settings.max_input_tokens

        logger.info("Loading {} from {} on device={}", model_id, model_path, self.device)

        # MPS/CPU need float32 to avoid NaN; CUDA can use bfloat16
        torch_dtype = torch.float32 if self.device in ("mps", "cpu") else torch.bfloat16

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch_dtype,
            trust_remote_code=True,
        ).to(self.device)
        self.model.eval()

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
