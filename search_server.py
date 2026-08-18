"""Local BM25 paper-search web application.

Examples:
    python3 search_server.py --db /secure/corpus/paper_database.json
    cd /secure/corpus && python3 /path/to/search_server.py

The server binds only to 127.0.0.1 and loads exactly one selected JSON database.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse


BASE_DIR = Path(__file__).parent.resolve()
WEB_DIR = BASE_DIR / "web"
DATABASE_FILENAME = "paper_database.json"
TOKEN_PATTERN = re.compile(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", re.IGNORECASE)
FIELD_WEIGHTS = {"title": 4, "keywords": 3, "metadata": 2, "text": 1}


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_PATTERN.findall(text)]


class BM25PaperSearch:
    """A small, inspectable BM25 index over weighted paper metadata fields."""

    def __init__(self, papers: list[dict[str, object]]) -> None:
        self.papers = papers
        self.doc_terms: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.document_frequency: Counter[str] = Counter()

        for paper in papers:
            terms = Counter()
            terms.update(self._weighted_terms(str(paper["title"]), FIELD_WEIGHTS["title"]))
            terms.update(
                self._weighted_terms(
                    " ".join(paper.get("keywords", [])), FIELD_WEIGHTS["keywords"]
                )
            )
            terms.update(self._weighted_terms(self._metadata_text(paper), FIELD_WEIGHTS["metadata"]))
            terms.update(self._weighted_terms(str(paper.get("text", "")), FIELD_WEIGHTS["text"]))
            self.doc_terms.append(terms)
            self.doc_lengths.append(sum(terms.values()))
            self.document_frequency.update(terms.keys())

        self.avg_document_length = sum(self.doc_lengths) / len(self.doc_lengths)

    @staticmethod
    def _weighted_terms(text: str, weight: int) -> Counter[str]:
        return Counter({term: count * weight for term, count in Counter(tokenize(text)).items()})

    @staticmethod
    def _metadata_text(paper: dict[str, object]) -> str:
        metadata = paper.get("pdf_metadata", {})
        return " ".join(str(value) for value in metadata.values())

    def _idf(self, term: str) -> float:
        count = self.document_frequency[term]
        total = len(self.papers)
        return math.log(1 + (total - count + 0.5) / (count + 0.5))

    def search(self, query: str, limit: int = 20) -> list[dict[str, object]]:
        query_terms = list(dict.fromkeys(tokenize(query)))
        if not query_terms:
            return [self._result(paper, 0, []) for paper in self.papers[:limit]]

        k1, b = 1.5, 0.75
        results: list[dict[str, object]] = []
        for index, paper in enumerate(self.papers):
            score = 0.0
            for term in query_terms:
                frequency = self.doc_terms[index][term]
                if not frequency:
                    continue
                denominator = frequency + k1 * (
                    1 - b + b * self.doc_lengths[index] / self.avg_document_length
                )
                score += self._idf(term) * frequency * (k1 + 1) / denominator
            if score > 0:
                results.append(self._result(paper, score, self._matched_fields(paper, query_terms)))

        return sorted(results, key=lambda item: (-item["score"], item["title"]))[:limit]

    @staticmethod
    def _matched_fields(paper: dict[str, object], terms: list[str]) -> list[str]:
        fields = {
            "title": str(paper["title"]),
            "keywords": " ".join(paper.get("keywords", [])),
            "metadata": BM25PaperSearch._metadata_text(paper),
            "text": str(paper.get("text", "")),
        }
        return [name for name, value in fields.items() if set(terms) & set(tokenize(value))]

    @staticmethod
    def _result(paper: dict[str, object], score: float, matched_fields: list[str]) -> dict[str, object]:
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
            "matched_fields": matched_fields,
        }


def resolve_database_path(requested_path: Path | None) -> Path:
    """Use an explicit DB, or the database in the current working directory."""
    return requested_path.resolve() if requested_path else (Path.cwd() / DATABASE_FILENAME).resolve()


def load_database(database_path: Path) -> dict[str, object]:
    if not database_path.is_file():
        raise FileNotFoundError(
            f"Database not found: {database_path}. Run build_paper_db.py for the desired PDF folder first."
        )
    database: dict[str, object] = json.loads(database_path.read_text(encoding="utf-8"))
    if not database.get("papers") or not database.get("source_root"):
        raise ValueError(f"Unsupported or empty PDF database: {database_path}")
    return database


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "PaperSearch/1.0"

    @property
    def database(self) -> dict[str, object]:
        return self.server.database  # type: ignore[attr-defined]

    @property
    def search_engine(self) -> BM25PaperSearch:
        return self.server.search_engine  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            query = params.get("q", [""])[0]
            limit = min(max(int(params.get("limit", [20])[0]), 1), 50)
            results = self.search_engine.search(query, limit)
            self._send_json({"query": query, "count": len(results), "results": results})
            return
        if parsed.path == "/api/health":
            self._send_json({"status": "ok", "papers": len(self.search_engine.papers)})
            return
        if parsed.path.startswith("/api/papers/") and parsed.path.endswith("/pdf"):
            paper_id = unquote(parsed.path.removeprefix("/api/papers/").removesuffix("/pdf").strip("/"))
            self._serve_paper_pdf(paper_id)
            return
        if parsed.path in {"/", "/index.html"}:
            self._serve_file(WEB_DIR, "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._serve_file(WEB_DIR, "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_file(WEB_DIR, "app.js", "application/javascript; charset=utf-8")
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _send_json(self, data: dict[str, object]) -> None:
        self._send(HTTPStatus.OK, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _serve_file(self, root: Path, requested_path: str, content_type: str) -> None:
        candidate = (root / requested_path).resolve()
        if root not in candidate.parents or not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        self._send(HTTPStatus.OK, candidate.read_bytes(), content_type)

    def _serve_paper_pdf(self, paper_id: str) -> None:
        paper = next((item for item in self.search_engine.papers if item["id"] == paper_id), None)
        if paper is None:
            self.send_error(HTTPStatus.NOT_FOUND, "Paper not found")
            return
        root = Path(self.database["source_root"]).resolve()
        candidate = (root / paper["source"]["relative_path"]).resolve()
        if root not in candidate.parents or not candidate.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "PDF not found")
            return
        self._send(HTTPStatus.OK, candidate.read_bytes(), "application/pdf")

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a local BM25 PDF search server.")
    parser.add_argument("--db", type=Path, help="JSON database to load (default: ./paper_database.json)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    database_path = resolve_database_path(args.db)
    database = load_database(database_path)
    server = ThreadingHTTPServer(("127.0.0.1", 8000), RequestHandler)
    server.database = database  # type: ignore[attr-defined]
    server.search_engine = BM25PaperSearch(database["papers"])  # type: ignore[attr-defined]
    print(f"Paper search running at http://127.0.0.1:8000\nDatabase: {database_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
