"""Install the Korean-to-English Transformer model for offline searching.

Examples:
    python3 install_ko_en_model.py
    python3 install_ko_en_model.py --from-dir /secure/models/opus-mt-ko-en

The download mode gets only the public translation model.  It never reads PDF
files.  The server then loads this local directory with network disabled.
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from translation_model import MODEL_DIR, MODEL_REPOSITORY, configure_model_environment

configure_model_environment()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Install the local Helsinki Korean-to-English translation model."
    )
    parser.add_argument(
        "--from-dir",
        type=Path,
        metavar="MODEL_DIRECTORY",
        help="Copy a pre-downloaded model directory without network access.",
    )
    return parser.parse_args()


def verify_model() -> None:
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
    AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR, local_files_only=True)


def main() -> None:
    args = parse_args()
    if args.from_dir:
        source_dir = args.from_dir.expanduser().resolve()
        if not (source_dir / "config.json").is_file():
            raise FileNotFoundError(f"Transformer model directory is invalid: {source_dir}")
        if source_dir != MODEL_DIR.resolve():
            shutil.copytree(source_dir, MODEL_DIR, dirs_exist_ok=True)
    elif not (MODEL_DIR / "config.json").is_file():
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=MODEL_REPOSITORY,
            local_dir=MODEL_DIR,
            ignore_patterns=["*.h5", "*.msgpack", "*.ot", "flax_model.*", "tf_model.*"],
        )

    verify_model()
    print(f"Installed and verified local Korean-to-English model: {MODEL_DIR}")


if __name__ == "__main__":
    main()
