import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_item_standard_v2 import sample
from item_screening_orchestrator import screen

class OrchestratorTests(unittest.TestCase):
    def test_missing_external_checks_remain_pending(self):
        result = screen(sample())
        self.assertEqual(result["stages"]["evidence"]["status"], "pending")
        self.assertEqual(result["stages"]["blind_model"]["status"], "pending")
        self.assertEqual(result["stages"]["human_review"]["status"], "pending")
        self.assertFalse(result["can_publish"])
    def test_verified_passage_and_blind_answer(self):
        item = sample()
        item["evidence"][0]["excerpt"] = "Evidence text"
        passages = {"p1": {"textbook_id": "t1", "pdf_page": 1, "text": "Evidence text"}}
        result = screen(item, passages=passages,
                        embedding=[1, 0], neighbors=[{"item_id": "other", "embedding": [0, 1]}],
                        blind_response={"item_id": "new-1", "key": ["A"]})
        self.assertEqual(result["stages"]["evidence"]["status"], "pass")
        self.assertEqual(result["stages"]["duplicates"]["status"], "pass")
        self.assertEqual(result["stages"]["blind_model"]["status"], "pass")
        self.assertEqual(result["stages"]["human_review"]["status"], "pending")
        self.assertFalse(result["can_publish"])
    def test_semantic_duplicate_flags(self):
        item = sample()
        result = screen(item, embedding=[1, 0],
                        neighbors=[{"item_id": "old", "embedding": [1, 0]}])
        self.assertEqual(result["stages"]["duplicates"]["status"], "flag")
    def test_blind_disagreement_routes_to_clinical_review(self):
        result = screen(sample(), blind_response={"item_id": "new-1", "key": ["B"]})
        self.assertEqual(result["next_state"], "needs_clinical_review")

if __name__ == "__main__":
    unittest.main()
