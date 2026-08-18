import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from pypdf import PdfWriter

from build_paper_db import build_database, filename_title, output_path_for, split_metadata_list
from build_chunked_paper_db import build_chunked_database, split_text
from search_server import BM25PaperSearch, resolve_database_path, tokenize


TEST_PAPERS = [
    {
        "id": "PDF-vector",
        "title": "Energy-Aware Vector Retrieval",
        "authors": ["Test Author"],
        "keywords": ["vector search", "retrieval"],
        "pdf_metadata": {},
        "preview": "",
        "text": "Approximate vector retrieval reduces energy use on edge devices.",
        "document_status": "text extracted",
        "source": {"relative_path": "vector.pdf"},
    },
    {
        "id": "PDF-materials",
        "title": "Monolayer Molybdenum Disulfide Growth",
        "authors": ["Test Author"],
        "keywords": ["MoS2", "growth"],
        "pdf_metadata": {},
        "preview": "",
        "text": "Synthetic materials-science test record.",
        "document_status": "text extracted",
        "source": {"relative_path": "materials.pdf"},
    },
]


class PaperSearchTests(unittest.TestCase):
    def test_tokenize_normalizes_case(self):
        self.assertEqual(tokenize("MoS2 Growth"), ["mos2", "growth"])

    def test_filename_is_a_title_fallback(self):
        self.assertEqual(filename_title(Path("A_test-paper.pdf")), "A test paper")

    def test_metadata_lists_support_common_separators(self):
        self.assertEqual(split_metadata_list("Kim; Lee, Park"), ["Kim", "Lee", "Park"])

    def test_default_database_is_created_inside_pdf_folder(self):
        self.assertEqual(
            output_path_for(Path("/tmp/corpus"), None),
            Path("/tmp/corpus/paper_database.json").resolve(),
        )

    def test_server_default_database_uses_current_folder(self):
        self.assertEqual(resolve_database_path(None), Path.cwd() / "paper_database.json")

    def test_format_agnostic_builder_indexes_a_pdf_without_fixed_headings(self):
        with TemporaryDirectory() as temporary_directory:
            pdf_path = Path(temporary_directory) / "unstructured.pdf"
            writer = PdfWriter()
            writer.add_blank_page(width=612, height=792)
            writer.add_metadata({"/Title": "Metadata-only PDF", "/Author": "Test Author"})
            with pdf_path.open("wb") as file:
                writer.write(file)

            database = build_database(Path(temporary_directory))

        self.assertEqual(database["paper_count"], 1)
        paper = database["papers"][0]
        self.assertEqual(paper["title"], "Metadata-only PDF")
        self.assertEqual(paper["authors"], ["Test Author"])
        self.assertIn("relative_path", paper["source"])

    def test_retrieval_ranks_title_and_keyword_matches(self):
        results = BM25PaperSearch(TEST_PAPERS).search("vector retrieval")
        self.assertEqual(results[0]["id"], "PDF-vector")
        self.assertIn("title", results[0]["matched_fields"])

    def test_retrieval_finds_materials_paper(self):
        results = BM25PaperSearch(TEST_PAPERS).search("MoS2 growth")
        self.assertEqual(results[0]["id"], "PDF-materials")

    def test_empty_query_returns_collection(self):
        self.assertEqual(len(BM25PaperSearch(TEST_PAPERS).search("")), 2)

    def test_chunked_database_preserves_parent_metadata_and_overlap(self):
        database = {"papers": [{**TEST_PAPERS[0], "text": "abcdefghij"}], "source_root": "/tmp/papers"}

        chunked = build_chunked_database(database, chunk_size=4, chunk_overlap=1)

        self.assertEqual(chunked["chunk_count"], 3)
        self.assertEqual([chunk["text"] for chunk in chunked["papers"]], ["abcd", "defg", "ghij"])
        self.assertEqual(chunked["papers"][1]["parent"]["id"], "PDF-vector")
        self.assertEqual(chunked["papers"][1]["chunk"]["overlap_characters"], 1)

    def test_chunk_size_must_exceed_overlap(self):
        with self.assertRaises(ValueError):
            split_text("test", chunk_size=10, chunk_overlap=10)


if __name__ == "__main__":
    unittest.main()
