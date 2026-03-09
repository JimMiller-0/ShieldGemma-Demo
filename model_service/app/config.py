import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from loguru import logger


MODEL_ID = "google/shieldgemma-2b"
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/app/models"))


def get_best_device() -> str:
    if os.environ.get("COMPUTE_DEVICE"):
        return os.environ["COMPUTE_DEVICE"]
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


@dataclass
class Settings:
    compute_device: str = field(default_factory=get_best_device)
    model_id: str = field(default_factory=lambda: os.environ.get("MODEL_ID", MODEL_ID))
    model_dir: Path = field(default_factory=lambda: MODEL_DIR)
    max_input_tokens: int = 4096
    max_payload_size: int = 10240
    log_level: str = field(default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO"))
    port: int = field(default_factory=lambda: int(os.environ.get("PORT", "8080")))

    @property
    def model_path(self) -> Path:
        safe_id = self.model_id.replace("/", "_--_")
        return self.model_dir / safe_id


settings = Settings()

logger.info(
    "Model service config: device={}, model={}, model_dir={}",
    settings.compute_device,
    settings.model_id,
    settings.model_dir,
)
