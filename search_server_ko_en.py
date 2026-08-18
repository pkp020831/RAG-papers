"""Local BM25 search server with offline Korean-to-English query translation.

Example:
    python3 search_server_ko_en.py --db /secure/corpus/paper_database.json

The translation step uses an installed Korean-to-English Transformer model on
this computer.  After the one-time model installation, it makes no network
call, does not send PDFs or queries externally, and does not use an external
LLM.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlparse

from search_server import BM25PaperSearch, RequestHandler, load_database, resolve_database_path
from translation_model import MODEL_DIR, configure_model_environment


BASE_DIR = Path(__file__).parent.resolve()
KO_EN_WEB_DIR = BASE_DIR / "web_ko_en"
BASE_WEB_DIR = BASE_DIR / "web"
DEFAULT_PORT = 8001
HANGUL_PATTERN = re.compile(r"[가-힣]")


class TranslationModel(Protocol):
    def translate(self, text: str) -> str: ...


@dataclass(frozen=True)
class TranslationResult:
    original_query: str
    translated_query: str
    translation_used: bool
    engine: str


class LocalTransformerModel:
    """Run a pre-downloaded translation model without a network fallback."""

    def __init__(self) -> None:
        configure_model_environment()
        try:
            import torch
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as error:
            raise RuntimeError(
                "Translation dependencies are missing. Run: python3 -m pip install -r requirements.txt"
            ) from error
        if not (MODEL_DIR / "config.json").is_file():
            raise RuntimeError(
                "Korean-to-English model is not installed. Run: python3 install_ko_en_model.py"
            )
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR, local_files_only=True)
        except OSError as error:
            raise RuntimeError(
                "The local Korean-to-English model is incomplete. "
                "Run: python3 install_ko_en_model.py"
            ) from error
        self.torch = torch
        self.model.eval()
        self._lock = Lock()

    def translate(self, text: str) -> str:
        encoded = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        with self._lock, self.torch.inference_mode():
            generated = self.model.generate(**encoded, num_beams=4, max_new_tokens=128)
        return self.tokenizer.batch_decode(generated, skip_special_tokens=True)[0].strip()


class TransformerKoreanEnglishTranslator:
    """Translate a complete Korean query with a local Transformer model."""

    engine_name = "Helsinki OPUS-MT + Transformers (ko→en local model)"

    def __init__(self, model: TranslationModel | None = None) -> None:
        self.model = model or LocalTransformerModel()

    def translate(self, query: str) -> TranslationResult:
        original_query = query.strip()
        if not HANGUL_PATTERN.search(original_query):
            return TranslationResult(
                original_query=original_query,
                translated_query=original_query,
                translation_used=False,
                engine=self.engine_name,
            )

        translated = self.model.translate(original_query).strip()
        if not translated:
            raise RuntimeError("The local translation model returned an empty translation.")
        return TranslationResult(
            original_query=original_query,
            translated_query=translated,
            translation_used=True,
            engine=self.engine_name,
        )


class KoreanEnglishRequestHandler(RequestHandler):
    """Keeps the base server's PDF routing while adding query translation."""

    @property
    def translator(self) -> TransformerKoreanEnglishTranslator:
        return self.server.translator  # type: ignore[attr-defined]

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        parsed = urlparse(self.path)
        if parsed.path == "/api/search":
            params = parse_qs(parsed.query)
            original_query = params.get("q", [""])[0]
            limit = min(max(int(params.get("limit", [20])[0]), 1), 50)
            translation = self.translator.translate(original_query)
            results = self.search_engine.search(translation.translated_query, limit)
            self._send_json(
                {
                    "query": translation.original_query,
                    "translated_query": translation.translated_query,
                    "translation_used": translation.translation_used,
                    "translation_engine": translation.engine,
                    "count": len(results),
                    "results": results,
                }
            )
            return
        if parsed.path in {"/", "/index.html"}:
            self._serve_file(KO_EN_WEB_DIR, "index.html", "text/html; charset=utf-8")
            return
        if parsed.path == "/styles.css":
            self._serve_file(BASE_WEB_DIR, "styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/ko-styles.css":
            self._serve_file(KO_EN_WEB_DIR, "ko-styles.css", "text/css; charset=utf-8")
            return
        if parsed.path == "/app.js":
            self._serve_file(KO_EN_WEB_DIR, "app.js", "application/javascript; charset=utf-8")
            return
        super().do_GET()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run offline Korean-to-English BM25 PDF search.")
    parser.add_argument("--db", type=Path, help="JSON database to load (default: ./paper_database.json)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Local port (default: {DEFAULT_PORT})")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1 <= args.port <= 65535:
        raise ValueError("Port must be between 1 and 65535.")

    database_path = resolve_database_path(args.db)
    database = load_database(database_path)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), KoreanEnglishRequestHandler)
    server.database = database  # type: ignore[attr-defined]
    server.search_engine = BM25PaperSearch(database["papers"])  # type: ignore[attr-defined]
    server.translator = TransformerKoreanEnglishTranslator()  # type: ignore[attr-defined]
    print(
        f"Korean-to-English BM25 search running at http://127.0.0.1:{args.port}"
        f"\nDatabase: {database_path}"
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
