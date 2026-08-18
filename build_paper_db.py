"""Build a format-agnostic, local JSON search database from PDF files.

Examples:
    python3 build_paper_db.py
    python3 build_paper_db.py --pdf-dir /secure/corpus

This script performs local PDF parsing only. It makes no network calls and does
not use an LLM or external embedding service.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pypdf import PdfReader


DEFAULT_PDF_DIR = Path("output/pdf")
DATABASE_FILENAME = "paper_database.json"
METADATA_FIELDS = {
    "title": "/Title",
    "author": "/Author",
    "subject": "/Subject",
    "keywords": "/Keywords",
    "creator": "/Creator",
    "producer": "/Producer",
    "creation_date": "/CreationDate",
    "modification_date": "/ModDate",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\x00", " ")).strip()


def filename_title(path: Path) -> str:
    """Use the filename as a neutral fallback when a PDF has no title metadata."""
    return re.sub(r"[_-]+", " ", path.stem).strip()


def split_metadata_list(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,]", value) if item.strip()]


def extract_metadata(reader: PdfReader) -> dict[str, str]:
    metadata: dict[str, str] = {}
    raw_metadata: Any = reader.metadata or {}
    for name, pdf_key in METADATA_FIELDS.items():
        value = raw_metadata.get(pdf_key)
        if value is not None and normalize_text(str(value)):
            metadata[name] = normalize_text(str(value))
    return metadata


def extract_pdf(root: Path, path: Path) -> dict[str, object]:
    """Extract local information without requiring document-specific headings."""
    fingerprint = sha256(path)
    relative_path = path.relative_to(root).as_posix()
    title = filename_title(path)
    metadata: dict[str, str] = {}
    extracted_pages: list[str] = []
    errors: list[str] = []
    page_count = 0
    encrypted = False

    try:
        reader = PdfReader(path)
        encrypted = reader.is_encrypted
        if encrypted and reader.decrypt("") == 0:
            errors.append("Encrypted PDF: no password was supplied, so text was not extracted.")
        else:
            metadata = extract_metadata(reader)
            title = metadata.get("title", title)
            page_count = len(reader.pages)
            for page_number, page in enumerate(reader.pages, start=1):
                try:
                    extracted_pages.append(page.extract_text() or "")
                except Exception as error:
                    errors.append(f"Page {page_number}: {type(error).__name__}: {error}")
    except Exception as error:
        errors.append(f"PDF read failed: {type(error).__name__}: {error}")

    text = normalize_text("\n".join(extracted_pages))
    return {
        "id": f"PDF-{fingerprint[:20]}",
        "title": title,
        "authors": split_metadata_list(metadata.get("author", "")),
        "keywords": split_metadata_list(metadata.get("keywords", "")),
        "pdf_metadata": metadata,
        "preview": text[:1200],
        "text": text,
        "synthetic": path.name.startswith("synthetic_"),
        "document_status": "text extracted" if text else "metadata only",
        "extraction": {
            "text_characters": len(text),
            "pages_with_text": sum(bool(normalize_text(page)) for page in extracted_pages),
            "errors": errors,
        },
        "source": {
            "relative_path": relative_path,
            "filename": path.name,
            "page_count": page_count,
            "size_bytes": path.stat().st_size,
            "sha256": fingerprint,
            "encrypted": encrypted,
        },
    }


def build_database(pdf_dir: Path) -> dict[str, object]:
    root = pdf_dir.resolve()
    if not root.is_dir():
        raise NotADirectoryError(f"PDF directory not found: {root}")

    paths = sorted(path for path in root.rglob("*.pdf") if path.is_file())
    if not paths:
        raise FileNotFoundError(f"No PDF files found under {root}")

    papers = [extract_pdf(root, path) for path in paths]
    return {
        "schema_version": "2.0",
        "database_name": "local-pdf-search-db",
        "description": "Locally extracted PDF metadata and text for BM25 search. No external LLM or API is used.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": str(root),
        "paper_count": len(papers),
        "papers": papers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a local BM25-ready PDF JSON database.")
    parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR, help="PDF folder to recursively index")
    parser.add_argument(
        "--output",
        type=Path,
        help="Destination JSON file (default: paper_database.json inside --pdf-dir)",
    )
    return parser.parse_args()


def output_path_for(pdf_dir: Path, requested_output: Path | None) -> Path:
    """Keep each corpus database beside the PDFs unless explicitly overridden."""
    return requested_output.resolve() if requested_output else pdf_dir.resolve() / DATABASE_FILENAME


def main() -> None:
    args = parse_args()
    database = build_database(args.pdf_dir)
    output_path = output_path_for(args.pdf_dir, args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(database, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {database['paper_count']} PDFs from {database['source_root']} to {output_path}")


if __name__ == "__main__":
    main()
