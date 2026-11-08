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
    def test_sa_blind_numeric_scoring_and_units(self):
        item = {"item_id": "n", "format": "SA", "stem": "Calculate",
                "sa": {"answer": 5.0, "tolerance": 0.1, "unit": "mg",
                       "rounding": "nearest tenth", "worked_solution": "private"}}
        self.assertEqual(payload(item)["unit"], "mg")
        self.assertNotIn("answer", payload(item))
        self.assertNotIn("worked_solution", str(payload(item)))
        self.assertEqual(compare(item, {"item_id": "n", "answer": 5.05, "unit": "MG"}), [])
        for answer, unit in ((5.2, "mg"), (5, "mL"), (True, "mg"),
                             (float("nan"), "mg"), (float("inf"), "mg"),
                             (5, None), ("5", "mg")):
            with self.subTest(answer=answer, unit=unit):
                self.assertTrue(compare(item, {"item_id": "n", "answer": answer, "unit": unit}))

    def test_non_mc_not_falsely_passed(self):
        item = {"item_id": "n", "format": "SA", "stem": "Calculate"}
        self.assertTrue(compare(item, {"item_id": "n", "answer": 5}))

if __name__ == "__main__":
    unittest.main()
