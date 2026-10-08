from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Optional

from loguru import logger

try:
    from transformers import AutoTokenizer
except ImportError:
    AutoTokenizer = None


def configured_pool_size() -> int:
    """Return the configured tokenizer pool size from env, defaulting to 4 (min 2)."""
    raw = os.environ.get("TOKENIZER_POOL_SIZE", "4")
    try:
        val = int(raw)
        return max(val, 2)
    except ValueError:
        return 4


class TokenizerPool:
    """Async-safe pool of fast tokenizer instances.

    HuggingFace fast tokenizers (Rust backend) can have race conditions or GIL
    contention when called concurrently across threads. This pool maintains a
    set of independent tokenizer instances checked out via an asyncio queue.
    """

    def __init__(self, tokenizers: list[Any]):
        if not tokenizers:
            raise ValueError("TokenizerPool must contain at least one tokenizer")
        self._queue: asyncio.Queue[Any] = asyncio.Queue()
        self._size = len(tokenizers)
        for tok in tokenizers:
            self._queue.put_nowait(tok)

    @property
    def size(self) -> int:
        return self._size

    @classmethod
    def build(cls, model_path: str, size: Optional[int] = None) -> "TokenizerPool":
        if AutoTokenizer is None:
            raise RuntimeError(
                "transformers.AutoTokenizer is required to build TokenizerPool "
                "but is not importable."
            )
        target_size = size or configured_pool_size()
        tokenizers = []
        for i in range(target_size):
            try:
                tok = AutoTokenizer.from_pretrained(model_path)
                tokenizers.append(tok)
            except Exception:
                logger.exception("Failed to initialize tokenizer instance {} for pool", i)
                if not tokenizers:
                    raise
                break
        return cls(tokenizers)

    @asynccontextmanager
    async def checkout(self) -> AsyncIterator[Any]:
        """Check out a tokenizer instance and return it upon exit."""
        tok = await self._queue.get()
        try:
            yield tok
        finally:
            self._queue.put_nowait(tok)
