import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_extraction import import_passages

class CentralImportQualityTests(unittest.TestCase):
    def test_low_text_rejected_before_db(self):
        with self.assertRaisesRegex(ValueError, "Unresolved extraction review"):
            import_passages(None, {"low_text_pages":[2], "ocr_failed_pages":[],
                                  "requires_ocr_review":True}, None)
    def test_ocr_failure_rejected_before_db(self):
        with self.assertRaisesRegex(ValueError, "Unresolved extraction review"):
            import_passages(None, {"low_text_pages":[], "ocr_failed_pages":[5],
                                  "requires_ocr_review":False}, None)
    def test_malformed_page_metadata_rejected_before_db(self):
        with self.assertRaisesRegex(ValueError, "Invalid extraction review metadata"):
            import_passages(None, {"low_text_pages":["2"], "ocr_failed_pages":[]}, None)
if __name__ == "__main__":
    unittest.main()
