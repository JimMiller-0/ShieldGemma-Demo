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


def main():
    safe_id = MODEL_ID.replace("/", "_--_")
    dest = MODEL_DIR / safe_id

    if dest.exists() and any(dest.iterdir()):
        print(f"Model already exists at {dest}. Skipping download.")
        print("Delete the directory to force re-download.")
        return

    dest.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {MODEL_ID} to {dest}...")
    print("This may take several minutes depending on your connection.")

    snapshot_download(
        repo_id=MODEL_ID,
        local_dir=str(dest),
        local_dir_use_symlinks=False,
    )

    print(f"Download complete: {dest}")


if __name__ == "__main__":
    main()
