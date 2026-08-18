"""Create a balanced 100-item Korean question-to-paper evaluation set."""
import json
from pathlib import Path

db = json.loads(Path("papers/paper_database.json").read_text())
topics = [
"평형 전파를 이용한 종단간 아날로그 신경망 학습", "멤리스터 기반 평형 전파의 학습 동역학", "상변화 메모리 기술의 원리와 발전", "상변화 메모리 기술의 최근 진전", "저항성 크로스포인트 배열에서 심층신경망 학습을 위한 제로 시프팅", "저항성 소자 배열에서 신경망을 훈련하는 알고리즘", "Tiki-Taka를 이용한 잡음 많은 아날로그 하드웨어의 신경망 훈련", "IGZO TFT 커패시터 시냅스와 retention-centric Tiki-Taka의 공동 최적화", "대규모 병렬 아날로그 온칩 학습 중 교란 완화", "국소 학습 신경망을 위한 결함 허용 멤리스터 크로스바 회로", "온라인 증분 학습을 위한 저랭크 평형 전파 아날로그 가속기", "멤리스터 크로스바를 이용한 activity-difference 신경망 학습", "프로세서 없이 비선형 아날로그 네트워크에서 나타나는 머신러닝", "비선형 저항성 네트워크의 보편 근사 정리", "1.5비트 ADC와 IGZO TFT 업데이트 셀을 사용하는 에너지 효율적 온칩 학습", "금속 계면활성층으로 상변화 메모리 셀의 저항 드리프트를 안정화하는 방법", "2차원 FET의 단일체 3D 집적으로 SRAM 셀을 스케일링하는 방법", "상보형 2차원 전계효과 트랜지스터의 단일체 3D 집적", "육방정 질화붕소 유전체와 고응집에너지 금속 게이트를 사용하는 2차원 트랜지스터", "고밀도 비아를 갖는 2차원 소재의 단일체·이종 3D 집적",
]
forms = [
"{topic}을 직접 다루는 논문은 무엇인가?",
"{topic}을 연구하려면 가장 관련 있는 논문은 무엇인가?",
"다음 주제에 가장 가까운 논문을 고르시오: {topic}.",
"{topic}이 핵심 기여인 논문은 무엇인가?",
"{topic} 문제를 이해하는 데 가장 적합한 논문은 무엇인가?",
]
items = []
for paper, topic in zip(db["papers"], topics, strict=True):
    for form in forms:
        items.append({
            "question_id": f"KQ{len(items)+1:03d}",
            "question": form.format(topic=topic),
            "answer_paper_id": paper["id"],
            "answer_title": paper["title"],
            "answer_evidence": f"논문 제목 '{paper['title']}'이(가) {topic}을 직접 명시한다.",
            "question_type": "direct_topic" if len(items) % 5 == 0 else "semantic_topic",
        })
output = {"dataset_name": "balanced_korean_paper_question_answer_set", "item_count": len(items), "papers_per_answer": 5, "items": items}
Path("papers/korean_question_answer_set_100.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print(f"Wrote {len(items)} Korean questions")
