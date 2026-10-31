import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_screening_blind_handoff_v2 import attach

def report():
    return {"stages": {k: {"status": "pass", "issues": []} for k in
            ("schema", "deterministic_text", "math", "evidence", "duplicates", "blind_model", "human_review")},
            "next_state": "draft", "can_publish": False}

def blind(status="pass", issues=None):
    return {"status": status, "issues": [] if issues is None else issues,
            "generator_model_id": "model-a", "reviewer_model_id": "model-b",
            "human_review_required": True, "can_publish": False}

class BlindHandoffTests(unittest.TestCase):
    def test_success_does_not_approve_or_modify_input(self):
        original = report()
        result = attach(original, blind())
        self.assertEqual(result["stages"]["blind_model"]["status"], "pass")
        self.assertEqual(result["stages"]["human_review"]["status"], "pending")
        self.assertFalse(result["can_publish"])
        self.assertEqual(original["stages"]["human_review"]["status"], "pass")
    def test_disagreement_routes_to_clinical_review(self):
        result = attach(report(), blind("flag", [{"rule_id": "R-12.1"}]))
        self.assertEqual(result["next_state"], "needs_clinical_review")
        self.assertFalse(result["screening_complete"])
    def test_same_model_rejected(self):
        value = blind()
        value["reviewer_model_id"] = "model-a"
        with self.assertRaises(ValueError): attach(report(), value)
    def test_unverified_claim_rejected(self):
        value = blind()
        value["can_publish"] = True
        with self.assertRaises(ValueError): attach(report(), value)

if __name__ == "__main__":
    unittest.main()
