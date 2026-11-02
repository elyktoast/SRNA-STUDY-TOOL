import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_independent_blind_v2 import review

ITEM = {"item_id": "new-1", "format": "MC", "stem": "Which option is correct?",
        "options": [{"id": k, "text": k + " option"} for k in "ABCD"],
        "key": ["B"], "rationale": {"why_key_wins": "Secret"},
        "evidence": [{"excerpt": "Private textbook"}]}

class BlindReviewTests(unittest.TestCase):
    def test_separate_model_gets_no_key_or_rationale(self):
        received = []
        def reviewer(payload):
            received.append(payload)
            return {"item_id": "new-1", "key": ["B"]}
        result = review(ITEM, reviewer, generator_model_id="generator-v1",
                        reviewer_model_id="reviewer-v2")
        self.assertEqual(result["status"], "pass")
        self.assertNotIn("key", received[0])
        self.assertNotIn("rationale", received[0])
        self.assertNotIn("evidence", received[0])
        self.assertFalse(result["can_publish"])
    def test_same_model_rejected(self):
        with self.assertRaises(ValueError):
            review(ITEM, lambda x: {}, generator_model_id="same", reviewer_model_id="same")
    def test_disagreement_flagged(self):
        result = review(ITEM, lambda x: {"item_id": "new-1", "key": ["C"]},
                        generator_model_id="a", reviewer_model_id="b")
        self.assertEqual(result["status"], "flag")

if __name__ == "__main__":
    unittest.main()
