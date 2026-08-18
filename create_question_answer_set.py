"""Create a balanced 100-item English question-to-paper evaluation set."""
import json
from pathlib import Path

db = json.loads(Path("papers/paper_database.json").read_text())
topics = [
"end-to-end analog neural-network training with equilibrium propagation", "learning dynamics of memristor-based equilibrium propagation", "the foundations and technology of phase-change memory", "recent progress in phase-change memory technology", "zero-shifting for deep-neural-network training on resistive cross-point arrays", "training algorithms for resistive device arrays", "training neural networks on noisy analog hardware with Tiki-Taka", "co-optimizing IGZO TFT capacitor synapses with retention-centric Tiki-Taka", "disturbance-aware mitigation during massively parallel analog on-chip training", "defect-tolerant memristor crossbar circuits for local learning", "low-rank equilibrium propagation for online incremental analog learning", "activity-difference training using memristor crossbars", "emergent machine learning in a nonlinear analog network without a processor", "universal approximation by nonlinear resistive networks", "an energy-efficient on-chip training system using 1.5-bit ADCs and IGZO TFT update cells", "a metallic surfactant layer that stabilizes resistance drift in a phase-change memory cell", "scaling SRAM cells through monolithic 3D integration of 2D FETs", "monolithic 3D integration of complementary 2D field-effect transistors", "2D-material transistors with hexagonal-boron-nitride dielectrics and high-cohesive-energy metal gates", "high-density-via monolithic and heterogeneous 3D integration of 2D materials",
]
forms = [
"Which paper is specifically about {topic}?",
"For a study of {topic}, which single paper is the closest match?",
"Which paper should be selected when the research question concerns {topic}?",
"Identify the paper whose central contribution is {topic}.",
"Which paper best matches this technical focus: {topic}?",
]
items = []
for paper, topic in zip(db["papers"], topics, strict=True):
    for form in forms:
        items.append({
            "question_id": f"Q{len(items)+1:03d}",
            "question": form.format(topic=topic),
            "answer_paper_id": paper["id"],
            "answer_title": paper["title"],
            "answer_evidence": f"The title explicitly identifies the paper as '{paper['title']}', which directly covers {topic}.",
            "question_type": "exact_title" if len(items) % 5 == 0 else "topic_match",
        })
output = {"dataset_name": "balanced_paper_question_answer_set", "item_count": len(items), "papers_per_answer": 5, "items": items}
Path("papers/question_answer_set_100.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote {len(items)} questions")
