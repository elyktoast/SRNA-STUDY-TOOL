import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_retrieval_benchmark_v2 import evaluate

class PageReferenceTests(unittest.TestCase):
    def test_correct_physical_page(self):
        case = [{"query":"airway", "expected_passage_ids":["p1"], "expected_pdf_pages":{"p1":8}}]
        result = evaluate(lambda q: [{"passage_id":"p1","pdf_page_start":8,"pdf_page_end":8}],case)
        self.assertTrue(result["passed"])
    def test_wrong_page_fails_even_when_passage_found(self):
        case = [{"query":"airway", "expected_passage_ids":["p1"], "expected_pdf_pages":{"p1":8}}]
        result = evaluate(lambda q: [{"passage_id":"p1","pdf_page_start":9,"pdf_page_end":9}],case)
        self.assertFalse(result["passed"])
        self.assertEqual(result["recall_at_k"],1)
    def test_missing_page_metadata_fails(self):
        case = [{"query":"airway", "expected_passage_ids":["p1"], "expected_pdf_pages":{"p1":8}}]
        result = evaluate(lambda q: [{"passage_id":"p1"}],case)
        self.assertFalse(result["passed"])
    def test_invalid_page_fixture_rejected(self):
        case = [{"query":"airway", "expected_passage_ids":["p1"], "expected_pdf_pages":{"p1":0}}]
        with self.assertRaises(ValueError): evaluate(lambda q: [],case)
if __name__ == "__main__":
    unittest.main()
