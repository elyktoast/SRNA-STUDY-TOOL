import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_extraction_quality_v2 import assess

def manifest():
    return {"pdf_page_count": 12, "passage_count": 30,
            "status": "extracted_not_indexed",
            "page_numbering": "physical_pdf_page_1_based",
            "citation_verified": False, "ocr_attempted": True,
            "low_text_pages": [3, 7], "ocr_failed_pages": [7],
            "ocr_pages": [5]}

class ExtractionGateTests(unittest.TestCase):
    def test_flags_unresolved_pages(self):
        result = assess(manifest())
        self.assertEqual(result["unresolved_pdf_pages"], [3, 7])
        self.assertFalse(result["ready_for_unqualified_indexing"])
        self.assertFalse(result["printed_page_citations_verified"])
    def test_reviewed_pages_clear_gate_not_citations(self):
        result = assess(manifest(), reviewed_pages=[3, 7])
        self.assertTrue(result["ready_for_unqualified_indexing"])
        self.assertFalse(result["printed_page_citations_verified"])
    def test_rejects_out_of_range_review(self):
        with self.assertRaises(ValueError): assess(manifest(), reviewed_pages=[13])
    def test_rejects_false_citation_claim(self):
        value = manifest()
        value["citation_verified"] = True
        with self.assertRaises(ValueError): assess(value)
    def test_rejects_no_searchable_content(self):
        value = manifest()
        value["passage_count"] = 0
        with self.assertRaises(ValueError): assess(value)

if __name__ == "__main__":
    unittest.main()
