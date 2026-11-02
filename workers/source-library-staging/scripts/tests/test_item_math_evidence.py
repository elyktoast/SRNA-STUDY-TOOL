import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_math_checks import check as math_check
from item_evidence_checks import check as evidence_check

class GroundingTests(unittest.TestCase):
    def test_numeric_pass_and_fail(self):
        item = {"format": "SA", "sa": {"answer": 5, "tolerance": 0}}
        spec = {"operation": "divide", "operands": [100, 20]}
        self.assertEqual(math_check(item, spec), [])
        self.assertTrue(math_check(item, {"operation": "divide", "operands": [100, 0]}))
        self.assertTrue(math_check(item))
        item["sa"]["answer"] = 6
        self.assertTrue(math_check(item, spec))
    def test_evidence_resolves_and_excerpt_matches(self):
        item = {"evidence": [{"passage_id": "p1", "textbook_id": "t1", "pdf_page": 8,
                              "excerpt": "quoted passage"}]}
        passages = {"p1": {"textbook_id": "t1", "pdf_page": 8, "text": "A quoted passage appears."}}
        self.assertEqual(evidence_check(item, passages), [])
        item["evidence"][0]["pdf_page"] = 9
        self.assertTrue(evidence_check(item, passages))
        item["evidence"][0]["pdf_page"] = 8
        item["evidence"][0]["excerpt"] = "fabricated words"
        self.assertTrue(evidence_check(item, passages))

if __name__ == "__main__":
    unittest.main()
