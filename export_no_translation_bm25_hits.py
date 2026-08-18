"""Export every apparent hit from the untranslated Korean BM25 baseline."""
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import urlopen

items = json.loads(Path("papers/korean_question_answer_set_100.json").read_text())["items"]
report = {}
for name, port in (("paper_db_8000", 8000), ("chunk_db_8002", 8002)):
    hits = []
    for item in items:
        response = json.load(urlopen(f"http://127.0.0.1:{port}/api/search?q={quote(item['question'])}&limit=3"))
        results = response["results"]
        rank = next((index for index, result in enumerate(results, 1) if result["id"].startswith(item["answer_paper_id"])), None)
        if rank:
            hits.append({
                "question_id": item["question_id"],
                "question": item["question"],
                "expected_paper_id": item["answer_paper_id"],
                "expected_title": item["answer_title"],
                "rank": rank,
                "returned_titles": [result["title"] for result in results],
            })
    report[name] = {"hit_count": len(hits), "hits": hits}
Path("papers/untranslated_bm25_apparent_hits.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
print({name: data["hit_count"] for name, data in report.items()})
