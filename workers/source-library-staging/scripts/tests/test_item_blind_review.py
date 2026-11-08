import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_blind_review import payload, compare

class BlindReviewTests(unittest.TestCase):
    def test_blind_payload_excludes_key_and_evidence(self):
        item = {"item_id": "x", "format": "MC", "stem": "Which?",
                "options": [{"id": "A", "text": "Alpha", "error_pattern": None},
                            {"id": "B", "text": "Beta", "error_pattern": "misconception"}],
                "key": ["A"], "rationale": {"why_key_wins": "secret"},
                "evidence": [{"excerpt": "private"}]}
        result = payload(item)
        self.assertEqual(set(result), {"item_id", "format", "stem", "options"})
        self.assertNotIn("error_pattern", result["options"][0])
        self.assertEqual(compare(item, {"item_id": "x", "key": ["A"]}), [])
        self.assertTrue(compare(item, {"item_id": "x", "key": ["B"]}))
    def test_malformed_blind_answers_fail_closed(self):
        item = {"item_id": "x", "format": "MS", "stem": "Select",
                "key": ["A", "B"]}
        for response_key in (None, "A", [["A"], "B"], [{"id": "A"}],
                             ["A", "A", "B"], ["A"], ["B", "C"]):
            with self.subTest(response_key=response_key):
                issues = compare(item, {"item_id": "x", "key": response_key})
                self.assertTrue(issues)
                self.assertEqual(issues[0]["rule_id"], "R-12.1")

    def test_non_mc_not_falsely_passed(self):
        item = {"item_id": "n", "format": "SA", "stem": "Calculate"}
        self.assertTrue(compare(item, {"item_id": "n", "answer": 5}))

if __name__ == "__main__":
    unittest.main()
