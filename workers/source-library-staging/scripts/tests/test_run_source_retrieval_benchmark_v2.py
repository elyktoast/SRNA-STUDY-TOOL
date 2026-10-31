import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_source_retrieval_benchmark_v2 import run

OWNER = "11111111-1111-4111-8111-111111111111"
BOOK = "22222222-2222-4222-8222-222222222222"

class RetrievalIntegrationTests(unittest.TestCase):
    def test_owner_and_textbook_filter_forwarded(self):
        fixtures = [{"query": "airway", "textbook_id": BOOK,
                     "expected_passage_ids": ["p1"]}]
        with patch("run_source_retrieval_benchmark_v2.search",
                   return_value=[{"passage_id": "p1", "pdf_page_start": 8, "pdf_page_end": 8}]) as mock:
            report = run(object(), owner_uid=OWNER, fixtures=fixtures)
        self.assertTrue(report["passed"])
        self.assertEqual(mock.call_args.kwargs["textbook_id"], BOOK)
        self.assertEqual(mock.call_args.args[2], OWNER)
    def test_rejects_bad_owner_before_search(self):
        with patch("run_source_retrieval_benchmark_v2.search") as mock:
            with self.assertRaises(ValueError):
                run(object(), owner_uid="bad", fixtures=[{"query":"x","expected_passage_ids":["p"]}])
            mock.assert_not_called()
    def test_missing_passage_is_reported(self):
        with patch("run_source_retrieval_benchmark_v2.search", return_value=[]):
            result = run(object(), owner_uid=OWNER,
                         fixtures=[{"query":"hemodynamics","expected_passage_ids":["p2"]}])
        self.assertFalse(result["passed"])

if __name__ == "__main__":
    unittest.main()
