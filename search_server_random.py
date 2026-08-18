"""Deterministic random-result baseline using the same local search web API."""
from __future__ import annotations

import argparse
import hashlib
import random
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import Any

from search_server import BM25PaperSearch, RequestHandler, load_database, resolve_database_path


class RandomPaperSearch:
    def __init__(self, papers: list[dict[str, Any]], seed: int) -> None:
        self.papers = papers
        self.seed = seed

    def search(self, query: str, limit: int = 20) -> list[dict[str, object]]:
        digest = hashlib.sha256(f"{self.seed}:{query}".encode()).digest()
        indices = list(range(len(self.papers)))
        random.Random(digest).shuffle(indices)
        return [BM25PaperSearch._result(self.papers[index], 0.0, []) for index in indices[:limit]]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic random baseline search server.")
    parser.add_argument("--db", type=Path, help="JSON database to load")
    parser.add_argument("--port", type=int, default=8006)
    parser.add_argument("--seed", type=int, default=20260818)
    args = parser.parse_args()
    database_path = resolve_database_path(args.db)
    database = load_database(database_path)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), RequestHandler)
    server.database = database  # type: ignore[attr-defined]
    server.search_engine = RandomPaperSearch(database["papers"], args.seed)  # type: ignore[attr-defined]
    print(f"Random baseline search running at http://127.0.0.1:{args.port}\nDatabase: {database_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
