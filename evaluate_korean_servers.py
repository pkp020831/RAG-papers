"""Evaluate every local search server against one fixed shuffled Korean QA set."""

import json
import random
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen


SEED = 20260818
LIMIT = 3
SERVERS = {
    "8000_bm25_paper": 8000,
    "8001_ko_en_bm25_paper": 8001,
    "8002_bm25_chunk": 8002,
    "8003_ko_en_bm25_chunk": 8003,
    "8004_vector_chunk": 8004,
    "8005_vector_paper": 8005,
    "8006_random_paper": 8006,
    "8007_random_chunk": 8007,
}
POINTS_BY_RANK = {1: 1.0, 2: 0.5, 3: 0.2}


def search(port: int, question: str) -> list[dict[str, object]]:
    url = f"http://127.0.0.1:{port}/api/search?q={quote(question)}&limit={LIMIT}"
    with urlopen(url, timeout=20) as response:
        return json.load(response)["results"]


def result_rank(results: list[dict[str, object]], expected_paper_id: str) -> int | None:
    return next(
        (
            rank
            for rank, result in enumerate(results, start=1)
            if str(result["id"]).startswith(expected_paper_id)
        ),
        None,
    )


def main() -> None:
    source = Path("papers/korean_question_answer_set_100.json")
    items = json.loads(source.read_text(encoding="utf-8"))["items"]
    shuffled_items = list(items)
    random.Random(SEED).shuffle(shuffled_items)

    report: dict[str, object] = {
        "dataset": str(source),
        "question_count": len(shuffled_items),
        "shuffle_seed": SEED,
        "limit": LIMIT,
        "points_by_rank": POINTS_BY_RANK,
        "shuffled_question_ids": [item["question_id"] for item in shuffled_items],
        "servers": {},
    }

    for name, port in SERVERS.items():
        details = []
        ranks = {1: 0, 2: 0, 3: 0, "miss": 0}
        for item in shuffled_items:
            results = search(port, item["question"])
            rank = result_rank(results, item["answer_paper_id"])
            ranks[rank if rank is not None else "miss"] += 1
            details.append(
                {
                    "question_id": item["question_id"],
                    "expected_paper_id": item["answer_paper_id"],
                    "rank": rank,
                    "returned_paper_ids": [result["id"] for result in results],
                }
            )
        score = sum(POINTS_BY_RANK[rank] * ranks[rank] for rank in POINTS_BY_RANK)
        report["servers"][name] = {
            "port": port,
            "rank_counts": ranks,
            "score": score,
            "top_3_hit_rate": round(1 - ranks["miss"] / len(shuffled_items), 4),
            "details": details,
        }
        print(name, score, ranks)

    output = Path("papers/korean_fixed_shuffle_evaluation.json")
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
