"""Create a chunk-level JSON search database from an existing paper database.

The source database remains unchanged.  Each output record is one overlapping
text chunk, so it can be used directly by the existing BM25 search server.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_CHUNK_SIZE = 1_000
DEFAULT_CHUNK_OVERLAP = 200
DEFAULT_OUTPUT_FILENAME = "paper_database_chunked.json"


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping, whitespace-trimmed character chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")
    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap must be at least zero and smaller than chunk_size")
    if not text:
        return []

    step = chunk_size - chunk_overlap
    starts = range(0, max(len(text) - chunk_overlap, 1), step)
    return [
        text[start : start + chunk_size].strip()
        for start in starts
        if text[start : start + chunk_size].strip()
    ]


def chunk_paper(paper: dict[str, Any], chunk_size: int, chunk_overlap: int) -> list[dict[str, Any]]:
    """Copy searchable paper metadata into one record for each text chunk."""
    text = paper.get("text", "")
    if not isinstance(text, str):
        raise ValueError(f"Paper {paper.get('id', '<unknown>')} has a non-string text field")

    chunks = split_text(text, chunk_size, chunk_overlap)
    total = len(chunks)
    return [
        {
            **paper,
            "id": f"{paper['id']}-chunk-{index:04d}",
            "preview": chunk[:1200],
            "text": chunk,
            "chunk": {
                "index": index,
                "count": total,
                "character_start": (index - 1) * (chunk_size - chunk_overlap),
                "character_end": min((index - 1) * (chunk_size - chunk_overlap) + len(chunk), len(text)),
                "size_characters": len(chunk),
                "overlap_characters": chunk_overlap if index > 1 else 0,
            },
            "parent": {
                "id": paper["id"],
                "title": paper.get("title", ""),
                "source": paper.get("source", {}),
            },
        }
        for index, chunk in enumerate(chunks, start=1)
    ]


def build_chunked_database(database: dict[str, Any], chunk_size: int, chunk_overlap: int) -> dict[str, Any]:
    """Transform a paper-level database into a chunk-level database."""
    papers = database.get("papers")
    if not isinstance(papers, list):
        raise ValueError("Source database must contain a papers array")

    chunks = [chunk for paper in papers for chunk in chunk_paper(paper, chunk_size, chunk_overlap)]
    return {
        "schema_version": "3.0",
        "database_name": "local-pdf-search-db-chunked",
        "description": "Overlapping text chunks derived locally from a local PDF search database.",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_root": database.get("source_root", ""),
        "paper_count": len(papers),
        "chunk_count": len(chunks),
        "chunking": {
            "unit": "characters",
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
        "source_database": {
            "schema_version": database.get("schema_version"),
            "database_name": database.get("database_name"),
            "generated_at_utc": database.get("generated_at_utc"),
        },
        "papers": chunks,
    }


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(DEFAULT_OUTPUT_FILENAME)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a chunk-level JSON database from paper_database.json.")
    parser.add_argument("--input", type=Path, required=True, help="Source paper_database.json")
    parser.add_argument("--output", type=Path, help="Output path (default: paper_database_chunked.json beside --input)")
    parser.add_argument(
        "--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE, help="Characters per chunk (default: 1000)"
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=DEFAULT_CHUNK_OVERLAP,
        help="Characters shared by adjacent chunks (default: 200)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input.resolve()
    output_path = (args.output or default_output_path(input_path)).resolve()
    if input_path == output_path:
        raise ValueError("Output path must differ from the source database path")

    database = json.loads(input_path.read_text(encoding="utf-8"))
    chunked_database = build_chunked_database(database, args.chunk_size, args.chunk_overlap)
    output_path.write_text(json.dumps(chunked_database, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {chunked_database['chunk_count']} chunks from {chunked_database['paper_count']} papers to {output_path}")


if __name__ == "__main__":
    main()
