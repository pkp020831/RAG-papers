"""Local multilingual vector search over a JSON PDF database.

The server embeds Korean queries and English paper chunks in the same space;
no query translation or external API is used after the model is downloaded.
"""

from __future__ import annotations

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from search_server import RequestHandler, load_database, resolve_database_path


DEFAULT_MODEL_DIR = Path("models/multilingual-e5-small")


class MultilingualVectorSearch:
    def __init__(self, papers: list[dict[str, Any]], model_dir: Path) -> None:
        self.papers = papers
        self.model = SentenceTransformer(str(model_dir), local_files_only=True)
        documents = [self._document_text(paper) for paper in papers]
        self.vectors = self.model.encode_document(
            documents, normalize_embeddings=True, show_progress_bar=True, batch_size=32
        )

    @staticmethod
    def _document_text(paper: dict[str, Any]) -> str:
        return "\n".join(
            [
                str(paper.get("title", "")),
                " ".join(paper.get("keywords", [])),
                str(paper.get("text", "")),
            ]
        )

    def search(self, query: str, limit: int = 20) -> list[dict[str, object]]:
        if not query.strip():
            return [self._result(paper, 0.0) for paper in self.papers[:limit]]
        query_vector = self.model.encode_query(query, normalize_embeddings=True)
        scores = np.asarray(self.vectors @ query_vector)
        indices = np.argsort(-scores)[:limit]
        return [self._result(self.papers[int(index)], float(scores[int(index)])) for index in indices]

    @staticmethod
    def _result(paper: dict[str, Any], score: float) -> dict[str, object]:
        return {
            "id": paper["id"],
            "title": paper["title"],
            "authors": paper["authors"],
            "venue": paper.get("pdf_metadata", {}).get("subject", ""),
            "keywords": paper["keywords"],
            "preview": paper.get("preview", ""),
            "document_status": paper["document_status"],
            "pdf_url": "/api/papers/" + paper["id"] + "/pdf",
            "score": round(score, 4),
            "matched_fields": ["semantic_similarity"],
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local multilingual vector PDF search.")
    parser.add_argument("--db", type=Path, help="JSON database to load")
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL_DIR)
    parser.add_argument("--port", type=int, default=8004)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        raise ValueError("Port must be between 1 and 65535")
    database_path = resolve_database_path(args.db)
    database = load_database(database_path)
    engine = MultilingualVectorSearch(database["papers"], args.model.resolve())
    server = ThreadingHTTPServer(("127.0.0.1", args.port), RequestHandler)
    server.database = database  # type: ignore[attr-defined]
    server.search_engine = engine  # type: ignore[attr-defined]
    print(f"Multilingual vector search running at http://127.0.0.1:{args.port}\nDatabase: {database_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
