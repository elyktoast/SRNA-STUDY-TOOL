import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_retrieval_benchmark_v2 import evaluate

class RetrievalBenchmarkTests(unittest.TestCase):
    def test_matching_expected_passage(self):
        def search(q):
            return [{"passage_id": "p2"}, {"passage_id": "p1"}]
        report = evaluate(search, [{"query": "airway", "expected_passage_ids": ["p1"]}])
        self.assertTrue(report["passed"])
        self.assertEqual(report["recall_at_k"], 1)
        self.assertFalse(report["cases"][0]["first_result_relevant"])
    def test_missing_passage_fails(self):
        report = evaluate(lambda q: [], [{"query": "hemodynamics", "expected_passage_ids": ["p1"]}])
        self.assertFalse(report["passed"])
        self.assertEqual(report["recall_at_k"], 0)
    def test_missing_page_constrained_passage_fails_even_with_low_recall_threshold(self):
        fixtures = [{"query": "topic", "expected_passage_ids": ["p1", "p2"],
                     "expected_pdf_pages": {"p2": 9}}]
        report = evaluate(
            lambda q: [{"passage_id": "p1", "pdf_page_start": 3, "pdf_page_end": 3}],
            fixtures, min_recall_at_k=0.5)
        self.assertEqual(report["recall_at_k"], 0.5)
        self.assertFalse(report["cases"][0]["page_references_valid"])
        self.assertFalse(report["passed"])
    def test_rejects_invalid_fixture(self):
        with self.assertRaises(ValueError):
            evaluate(lambda q: [], [{"query": "", "expected_passage_ids": ["p1"]}])
    def test_deduplicates_repeated_search_results(self):
        report = evaluate(lambda q: [{"passage_id": "p1"}, {"passage_id": "p1"}],
                          [{"query": "topic", "expected_passage_ids": ["p1", "p2"]}])
        self.assertEqual(report["recall_at_k"], 0.5)
if __name__ == "__main__":
    unittest.main()
