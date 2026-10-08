"""Download ShieldGemma-2B model from HuggingFace to the local models directory.

Usage:
    python -m model_service.scripts.download_model

Set MODEL_DIR env var to change the destination (default: ./models).
"""

import os
import sys
from pathlib import Path

from huggingface_hub import snapshot_download


MODEL_ID = os.environ.get("MODEL_ID", "google/shieldgemma-2b")
MODEL_DIR = Path(os.environ.get("MODEL_DIR", "./models"))


def download_model(
    model_id: str | None = None,
    model_dir: Path | str | None = None,
    token: str | None = None,
) -> Path:
    target_id = model_id or MODEL_ID
    target_dir = Path(model_dir) if model_dir else MODEL_DIR
    auth_token = token or os.environ.get("HF_TOKEN")

    safe_id = target_id.replace("/", "_--_")
    dest = target_dir / safe_id

    if dest.exists() and any(dest.iterdir()):
        print(f"Model already exists at {dest}. Skipping download.")
        return dest

    dest.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {target_id} to {dest}...")

    snapshot_download(
        repo_id=target_id,
        local_dir=str(dest),
        local_dir_use_symlinks=False,
        token=auth_token,
    )

    print(f"Download complete: {dest}")
    return dest


def main():
    download_model()


if __name__ == "__main__":
    main()

