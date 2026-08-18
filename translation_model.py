"""Paths and local-only settings for the Korean-to-English translation model."""

from __future__ import annotations

import os
from pathlib import Path


PROJECT_DIR = Path(__file__).parent.resolve()
MODELS_DIR = PROJECT_DIR / "models"
MODEL_REPOSITORY = "Helsinki-NLP/opus-mt-ko-en"
MODEL_DIR = MODELS_DIR / "opus-mt-ko-en"


def configure_model_environment() -> None:
    """Keep the download cache and certificate configuration local to this project."""
    os.environ.setdefault("HF_HOME", str(MODELS_DIR / "huggingface-cache"))
    try:
        import certifi
    except ImportError:
        return
    os.environ.setdefault("SSL_CERT_FILE", certifi.where())
