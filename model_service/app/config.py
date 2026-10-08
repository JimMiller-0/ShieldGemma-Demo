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
    vllm_gpu_memory_utilization: float = field(
        default_factory=lambda: float(os.environ.get("VLLM_GPU_MEMORY_UTILIZATION", "0.9"))
    )
    max_model_len: int = field(
        default_factory=lambda: int(os.environ.get("MAX_MODEL_LEN", "4096"))
    )
    vllm_max_num_seqs: int = field(
        default_factory=lambda: int(os.environ.get("VLLM_MAX_NUM_SEQS", "64"))
    )
    vllm_enable_prefix_caching: bool = field(
        default_factory=lambda: os.environ.get("VLLM_ENABLE_PREFIX_CACHING", "true").lower()
        in ("1", "true", "yes", "on")
    )
    vllm_use_async_engine: bool = field(
        default_factory=lambda: os.environ.get("VLLM_USE_ASYNC_ENGINE", "true").lower()
        in ("1", "true", "yes", "on")
    )
    use_vllm: bool = field(
        default_factory=lambda: os.environ.get("USE_VLLM", "true").lower()
        in ("1", "true", "yes", "on")
    )

    def get_model_path(self, model_id: Optional[str] = None) -> Path:
        target_id = model_id or self.model_id
        safe_id = target_id.replace("/", "_--_")
        return self.model_dir / safe_id

    def get_registry_entry(self, model_id: Optional[str] = None):
        """Optional model registry lookup hook for per-model overrides."""
        return None

    @property
    def model_path(self) -> Path:
        return self.get_model_path(self.model_id)


settings = Settings()

logger.info(
    "Model service config: device={}, model={}, model_dir={}",
    settings.compute_device,
    settings.model_id,
    settings.model_dir,
)
