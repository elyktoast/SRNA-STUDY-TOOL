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

    def test_image_page_detected_without_claiming_ocr(self):
        import fitz
        doc = fitz.open(self.pdf)
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 12), False)
        doc[0].insert_image(fitz.Rect(80, 100, 120, 140), pixmap=pix)
        target = self.base / "with_image.pdf"
        doc.save(target)
        doc.close()
        result = module.extract(target, self.base / "image-index",
                                self.owner, self.owner + "/with_image.pdf")
        self.assertEqual(result["image_pages"], [1])
        self.assertEqual(result["low_text_details"], [])

    def test_ocr_recovers_text_from_scanned_page(self):
        import fitz
        source = fitz.open()
        page = source.new_page()
        pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 600, 160), False)
        pix.clear_with(255)
        image_doc = fitz.open()
        image_page = image_doc.new_page(width=600, height=160)
        image_page.insert_text((20, 85), "ANESTHESIA AIRWAY SAFETY", fontsize=28)
        pix = image_page.get_pixmap(matrix=fitz.Matrix(2, 2))
        page.insert_image(page.rect, pixmap=pix)
        target = self.base / "scanned.pdf"
        source.save(target)
        source.close()
        image_doc.close()
        out = self.base / "ocr-index"
        result = module.extract(target, out, self.owner,
                                self.owner + "/scanned.pdf", ocr=True)
        self.assertTrue(result["ocr_attempted"])
        if result["ocr_failed_pages"]:
            with fitz.open(target) as scanned:
                try:
                    scanned[0].get_textpage_ocr(language="eng", dpi=200, full=True)
                except Exception as exc:
                    self.fail(f"OCR engine failure on synthetic fixture: {type(exc).__name__}: {str(exc)[:300]}")
        self.assertEqual(result["ocr_pages"], [1], msg=f"OCR metadata: {result}")
        self.assertEqual(result["low_text_pages"], [1])
        self.assertTrue(result["requires_ocr_review"])
        passages = (out / "passages.jsonl").read_text(encoding="utf-8")
        self.assertIn("AIRWAY", passages.upper())

    def test_low_text_details_identify_blank_page_without_exposing_content(self):
        import fitz
        doc = fitz.open(self.pdf)
        doc.new_page()
        target = self.base / "blank_tail.pdf"
        doc.save(target)
        doc.close()
        result = module.extract(target, self.base / "blank-index",
                                self.owner, self.owner + "/blank_tail.pdf")
        self.assertEqual(result["low_text_pages"], [3])
        self.assertEqual(result["low_text_details"], [{
            "pdf_page": 3, "characters": 0, "has_images": False,
            "ocr_improved": False, "ocr_failed": False,
            "review_category": "blank_candidate_review",
        }])
        self.assertFalse(result["citation_verified"])

    def test_pdf_bookmarks_extracted_as_sections(self):
        import fitz
        doc = fitz.open(self.pdf)
        doc.set_toc([[1, "Airway", 1], [1, "Pharmacology", 2]])
        doc.save(self.base / "with_toc.pdf")
        doc.close()
        result = module.extract(self.base / "with_toc.pdf", self.base / "toc-index",
                                self.owner, self.owner + "/with_toc.pdf")
        self.assertEqual(result["section_count"], 2)
        sections = [json.loads(line) for line in
                    (self.base / "toc-index" / "sections.jsonl").read_text().splitlines()]
        self.assertEqual([s["start_page"] for s in sections], [1, 2])
        self.assertTrue(all(s["source"] == "pdf_bookmark" for s in sections))

    def test_unsafe_filename_rejected_before_output(self):
        unsafe = self.base / "book with spaces.pdf"
        unsafe.write_bytes(self.pdf.read_bytes())
        output = self.base / "unsafe-output"
        with self.assertRaisesRegex(ValueError, "filename"):
            module.extract(unsafe, output, self.owner, self.owner + "/book.pdf")
        self.assertFalse(output.exists())

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
