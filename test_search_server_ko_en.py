import unittest

from search_server import BM25PaperSearch
from search_server_ko_en import TransformerKoreanEnglishTranslator


PAPER = {
    "id": "PDF-test",
    "title": "Equilibrium Propagation for Neural Networks",
    "authors": [],
    "keywords": ["equilibrium propagation", "neural networks"],
    "pdf_metadata": {},
    "preview": "",
    "text": "An analog neural network is trained with equilibrium propagation.",
    "document_status": "text extracted",
    "source": {"relative_path": "test.pdf"},
}


class FakeTranslationModel:
    def __init__(self, translation: str) -> None:
        self.translation = translation
        self.requests: list[str] = []

    def translate(self, text: str) -> str:
        self.requests.append(text)
        return self.translation


class KoreanEnglishSearchTests(unittest.TestCase):
    def setUp(self):
        self.model = FakeTranslationModel("equilibrium propagation neural networks")
        self.translator = TransformerKoreanEnglishTranslator(self.model)

    def test_translates_the_complete_korean_query_with_the_model(self):
        query = "평형 전파를 사용하는 신경망 학습 방법"
        result = self.translator.translate(query)
        self.assertEqual(result.translated_query, "equilibrium propagation neural networks")
        self.assertTrue(result.translation_used)
        self.assertEqual(self.model.requests, [query])

    def test_preserves_english_query(self):
        result = self.translator.translate("noisy hardware")
        self.assertEqual(result.translated_query, "noisy hardware")
        self.assertFalse(result.translation_used)
        self.assertEqual(self.model.requests, [])

    def test_translated_query_retrieves_english_paper(self):
        result = self.translator.translate("평형 전파")
        results = BM25PaperSearch([PAPER]).search(result.translated_query)
        self.assertEqual(results[0]["id"], "PDF-test")


if __name__ == "__main__":
    unittest.main()
