"""Regression tests for source evidence handoff; no AI or database."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_evidence_checks import check
from item_source_reconciliation_v2 import reconcile

PASSAGE = {"passage_id": "p1", "textbook_id": "t1",
           "excerpt": "Patient’s airway — thoroughly  suctioned.",
           "pdf_page_start": 197}
CITATION = {"passage_id": "p1", "textbook_id": "t1",
            "excerpt": "Patient's airway - thoroughly suctioned.",
            "pdf_page": 197}

class EvidenceStageConsistencyTests(unittest.TestCase):
    def test_format_only_difference_passes_both_stages(self):
        self.assertEqual(reconcile({"evidence": [CITATION]}, [PASSAGE]), [])
        indexed = {"p1": {"textbook_id": "t1", "pdf_page": 197,
                          "text": PASSAGE["excerpt"]}}
        self.assertEqual(check({"evidence": [CITATION]}, indexed), [])

    def test_wrong_pdf_page_rejected(self):
        indexed = {"p1": {"textbook_id": "t1", "pdf_page": 197,
                          "text": PASSAGE["excerpt"]}}
        self.assertTrue(check({"evidence": [{**CITATION, "pdf_page": 198}]}, indexed))

    def test_invented_clinical_wording_rejected(self):
        indexed = {"p1": {"textbook_id": "t1", "pdf_page": 197,
                          "text": PASSAGE["excerpt"]}}
        self.assertTrue(check({"evidence": [{**CITATION, "excerpt": "Patient may be deeply sedated."}]}, indexed))

if __name__ == "__main__":
    unittest.main()
