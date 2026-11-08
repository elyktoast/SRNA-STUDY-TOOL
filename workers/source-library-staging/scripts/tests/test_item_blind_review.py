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

    def test_dd_blind_matching_scoring(self):
        pairs = {"L1": "R2", "L2": "R4", "L3": "R1", "L4": "R3"}
        item = {"item_id": "d", "format": "DD", "stem": "Match",
                "dd": {"left": [{"id": k, "text": k} for k in pairs],
                       "right": [{"id": "R" + str(i), "text": str(i)} for i in range(1, 5)],
                       "pairs": pairs},
                "rationale": {"why_key_wins": "secret"}}
        self.assertNotIn("pairs", payload(item))
        self.assertNotIn("rationale", payload(item))
        self.assertEqual(compare(item, {"item_id": "d", "pairs": dict(pairs)}), [])
        for wrong in ({}, {"L1": "R2"}, {"L1": "R2", "L2": "R2", "L3": "R1", "L4": "R3"},
                      {"L1": "R4", "L2": "R2", "L3": "R1", "L4": "R3"},
                      ["R2", "R4", "R1", "R3"], None):
            with self.subTest(wrong=wrong):
                self.assertTrue(compare(item, {"item_id": "d", "pairs": wrong}))

    def test_non_mc_not_falsely_passed(self):
        item = {"item_id": "n", "format": "SA", "stem": "Calculate"}
        self.assertTrue(compare(item, {"item_id": "n", "answer": 5}))

if __name__ == "__main__":
    unittest.main()
