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
import math
import re
from dataclasses import dataclass
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Lock
from typing import Protocol
from urllib.parse import parse_qs, unquote, urlparse

from search_server import BM25PaperSearch, RequestHandler, load_database, resolve_database_path, tokenize
from translation_model import MODEL_DIR, configure_model_environment


BASE_DIR = Path(__file__).parent.resolve()
KO_EN_WEB_DIR = BASE_DIR / "web_ko_en"
BASE_WEB_DIR = BASE_DIR / "web"
DEFAULT_PORT = 8001
HANGUL_PATTERN = re.compile(r"[가-힣]")

TRANSLATION_CANDIDATE_COUNT = 10
RESULTS_PER_VARIANT = 50
RRF_K = 60


class TranslationModel(Protocol):
    def translate(self, text: str) -> str: ...


@dataclass(frozen=True)
class TranslationResult:
    original_query: str
    translated_query: str
    translation_used: bool
    engine: str
    candidates: tuple["TranslationCandidate", ...]


@dataclass(frozen=True)
class TranslationCandidate:
    text: str
    model_score: float
    weight: float


@dataclass(frozen=True)
class SearchVariant:
    source: str
    query: str
    weight: float = 1.0


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
        return self.translate_candidates(text)[0][0]

    def translate_candidates(self, text: str) -> list[tuple[str, float]]:
        encoded = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=256)
        with self._lock, self.torch.inference_mode():
            generated = self.model.generate(
                **encoded,
                num_beams=TRANSLATION_CANDIDATE_COUNT,
                num_return_sequences=TRANSLATION_CANDIDATE_COUNT,
                max_new_tokens=128,
                return_dict_in_generate=True,
                output_scores=True,
            )
        texts = self.tokenizer.batch_decode(generated.sequences, skip_special_tokens=True)
        return list(zip((text.strip() for text in texts), generated.sequences_scores.tolist(), strict=True))


class TransformerKoreanEnglishTranslator:
    """Translate a complete Korean query with a local Transformer model."""

    engine_name = "Helsinki OPUS-MT + Transformers (ko→en local model)"

    def __init__(self, model: TranslationModel | None = None) -> None:
        self.model = model or LocalTransformerModel()

    def translate(self, query: str) -> TranslationResult:
        original_query = query.strip()
        if not HANGUL_PATTERN.search(original_query):
            candidate = TranslationCandidate(original_query, 0.0, 1.0)
            return TranslationResult(
                original_query=original_query,
                translated_query=original_query,
                translation_used=False,
                engine=self.engine_name,
                candidates=(candidate,),
            )

        generator = getattr(self.model, "translate_candidates", None)
        raw_candidates = generator(original_query) if callable(generator) else [(self.model.translate(original_query), 0.0)]
        candidates = self._candidates(raw_candidates)
        if not candidates:
            raise RuntimeError("The local translation model returned an empty translation.")
        return TranslationResult(
            original_query=original_query,
            translated_query=candidates[0].text,
            translation_used=True,
            engine=self.engine_name,
            candidates=tuple(candidates),
        )

    @staticmethod
    def _candidates(raw_candidates: list[tuple[str, float]]) -> list[TranslationCandidate]:
        """Deduplicate beam outputs and turn relative model scores into RRF weights."""
        unique: list[tuple[str, float]] = []
        seen: set[str] = set()
        for text, score in raw_candidates:
            normalized = text.strip()
            if normalized and normalized.casefold() not in seen:
                unique.append((normalized, float(score)))
                seen.add(normalized.casefold())
        if not unique:
            return []
        maximum = max(score for _, score in unique)
        unnormalized = [math.exp(score - maximum) for _, score in unique]
        total = sum(unnormalized)
        return [
            TranslationCandidate(text, score, weight / total)
            for (text, score), weight in zip(unique, unnormalized, strict=True)
        ]


def build_search_variants(translation: TranslationResult) -> list[SearchVariant]:
    """Search only English candidates; BM25 scores are fused by rank, not value."""
    return [
        SearchVariant(f"translation:{index}", candidate.text, candidate.weight)
        for index, candidate in enumerate(translation.candidates, start=1)
    ]


def rrf_search(
    search_engine: BM25PaperSearch, variants: list[SearchVariant], limit: int
) -> list[dict[str, object]]:
    """Fuse rank positions, not incomparable BM25 scores from different queries."""
    if not variants or not any(variant.query.strip() for variant in variants):
        return search_engine.search("", limit)

    fused: dict[str, dict[str, object]] = {}
    per_variant_limit = max(RESULTS_PER_VARIANT, limit)
    for variant in variants:
        # The current PDF index is English-token based.  BM25 treats a query
        # with no indexable tokens as an empty query and returns arbitrary
        # collection items, which must not influence RRF.
        if not tokenize(variant.query):
            continue
        for rank, result in enumerate(search_engine.search(variant.query, per_variant_limit), start=1):
            paper_id = str(result["id"])
            if paper_id not in fused:
                fused[paper_id] = {
                    **result,
                    "matched_fields": list(result["matched_fields"]),
                    "retrieved_by": [],
                    "score": 0.0,
                }
            item = fused[paper_id]
            item["score"] = float(item["score"]) + variant.weight / (RRF_K + rank)
            item["retrieved_by"].append(variant.source)  # type: ignore[union-attr]
            item["matched_fields"] = list(
                dict.fromkeys([*item["matched_fields"], *result["matched_fields"]])
            )

    ranked = sorted(
        fused.values(), key=lambda item: (-float(item["score"]), str(item["title"]))
    )[:limit]
    for item in ranked:
        item["score"] = round(float(item["score"]), 6)
    return ranked


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
            variants = build_search_variants(translation)
            results = rrf_search(self.search_engine, variants, limit)
            self._send_json(
                {
                    "query": translation.original_query,
                    "translated_query": translation.translated_query,
                    "translation_used": translation.translation_used,
                    "translation_engine": translation.engine,
                    "fusion_method": "reciprocal_rank_fusion",
                    "search_variants": [
                        {"source": variant.source, "query": variant.query} for variant in variants
                    ],
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
