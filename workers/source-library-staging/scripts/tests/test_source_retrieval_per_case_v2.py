import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_retrieval_benchmark_v2 import evaluate

class PerCaseRecallTests(unittest.TestCase):
    def test_aggregate_cannot_hide_failed_case(self):
        fixtures = [
            {"query": "good", "expected_passage_ids": ["a", "b", "c", "d", "e", "f", "g", "h", "i"]},
            {"query": "bad", "expected_passage_ids": ["missing"]},
        ]
        def search(query):
            return [{"passage_id": p} for p in "abcdefghi"] if query == "good" else []
        report = evaluate(search, fixtures, min_recall_at_k=0.8)
        self.assertEqual(report["recall_at_k"], 0.9)
        self.assertFalse(report["passed"])
        self.assertEqual(report["cases"][1]["recall_at_k"], 0)
    def test_all_cases_meet_threshold(self):
        fixtures = [{"query": "one", "expected_passage_ids": ["a"]},
                    {"query": "two", "expected_passage_ids": ["b"]}]
        report = evaluate(lambda q: [{"passage_id": "a" if q == "one" else "b"}], fixtures)
        self.assertTrue(report["passed"])

if __name__ == "__main__":
    unittest.main()
