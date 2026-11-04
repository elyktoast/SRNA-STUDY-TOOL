import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_source_reconciliation_v2 import reconcile

SOURCE = [{"passage_id": "p1", "textbook_id": "t1",
           "excerpt": "Clinical evidence about airway risk.", "pdf_page_start": 12}]
CITATION = {"passage_id": "p1", "textbook_id": "t1",
            "excerpt": "airway risk", "pdf_page": 12,
            "printed_page_verified": False}

class ReconciliationTests(unittest.TestCase):
    def test_valid_source_location(self):
        self.assertEqual(reconcile({"evidence": [CITATION]}, SOURCE), [])
    def test_invented_passage_blocked(self):
        self.assertTrue(reconcile({"evidence": [{**CITATION, "passage_id": "fake"}]}, SOURCE))
    def test_typography_and_spacing_only_are_accepted(self):
        source = [{**SOURCE[0], "excerpt": "Patient’s airway — thoroughly  suctioned."}]
        citation = {**CITATION, "excerpt": "Patient's airway - thoroughly suctioned."}
        self.assertEqual(reconcile({"evidence": [citation]}, source), [])

    def test_paraphrase_remains_blocked(self):
        source = [{**SOURCE[0], "excerpt": "Patient must be fully awake."}]
        citation = {**CITATION, "excerpt": "Patient may be mildly sedated."}
        self.assertTrue(reconcile({"evidence": [citation]}, source))

    def test_invented_excerpt_blocked(self):
        self.assertTrue(reconcile({"evidence": [{**CITATION, "excerpt": "not in book"}]}, SOURCE))
    def test_invented_page_blocked(self):
        self.assertTrue(reconcile({"evidence": [{**CITATION, "pdf_page": 999}]}, SOURCE))
    def test_model_cannot_verify_printed_page(self):
        self.assertTrue(reconcile({"evidence": [{**CITATION, "printed_page_verified": True}]}, SOURCE))
    def test_missing_evidence_blocked(self):
        self.assertTrue(reconcile({}, SOURCE))

if __name__ == "__main__":
    unittest.main()
