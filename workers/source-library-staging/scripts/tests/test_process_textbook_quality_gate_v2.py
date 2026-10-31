import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from process_textbook import process

class ProcessQualityTests(unittest.TestCase):
    def test_apply_refuses_unreviewed_low_text_before_database_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / "book.pdf"
            pdf.write_bytes(b"%PDF-mock")
            digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
            manifest = {
                "pdf_page_count": 4, "passage_count": 2, "sha256": digest,
                "requires_ocr_review": True, "low_text_pages": [2],
                "ocr_failed_pages": [2], "ocr_attempted": True, "ocr_pages": [],
                "status": "extracted_not_indexed", "citation_verified": False,
                "page_numbering": "physical_pdf_page_1_based"
            }
            with patch("process_textbook.extract", return_value=manifest), patch(
                    "process_textbook.validate", return_value=manifest):
                with self.assertRaisesRegex(ValueError, "Unresolved OCR"):
                    process(pdf, root / "index", "owner", "owner/book.pdf", apply=True)
                dry = process(pdf, root / "index", "owner", "owner/book.pdf", apply=False)
                self.assertEqual(dry["extraction_quality"]["unresolved_pdf_pages"], [2])
                self.assertFalse(dry["indexed"])
                self.assertFalse(dry["citation_verified"])

if __name__ == "__main__":
    unittest.main()
