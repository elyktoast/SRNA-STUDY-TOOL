"""Extractor smoke tests with an in-memory generated PDF; no credentials or network needed."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("extract_textbook", ROOT / "extract_textbook.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExtractorTests(unittest.TestCase):
    def setUp(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.pdf = self.base / "sample.pdf"
        doc = fitz.open()
        for text in ("Airway assessment and tracheal intubation", "Volatile anesthetic pharmacology and uptake"):
            page = doc.new_page()
            page.insert_text((72, 72), text)
        doc.save(self.pdf)
        doc.close()
        self.owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
        self.key = self.owner + "/sample.pdf"

    def test_two_page_extraction(self):
        out = self.base / "extracted"
        result = module.extract(self.pdf, out, self.owner, self.key)
        self.assertEqual(result["pdf_page_count"], 2)
        self.assertEqual(result["passage_count"], 2)
        self.assertFalse(result["citation_verified"])
        pages = [json.loads(line) for line in (out / "pages.jsonl").read_text().splitlines()]
        self.assertEqual([p["pdf_page"] for p in pages], [1, 2])
        self.assertIn("Airway", pages[0]["text"])

    def test_invalid_pdf_signature(self):
        self.pdf.write_bytes(b"not a pdf")
        with self.assertRaisesRegex(ValueError, "signature"):
            module.extract(self.pdf, self.base / "out", self.owner, self.key)

    def test_wrong_owner_prefix(self):
        with self.assertRaisesRegex(ValueError, "prefix"):
            module.extract(self.pdf, self.base / "out", self.owner, "another/sample.pdf")

    def test_output_directory_guard(self):
        with self.assertRaisesRegex(ValueError, "separate directory"):
            module.extract(self.pdf, self.base, self.owner, self.key)


if __name__ == "__main__":
    unittest.main()
