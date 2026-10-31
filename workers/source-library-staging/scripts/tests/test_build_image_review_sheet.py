"""Private local contact-sheet smoke tests."""
import json
import tempfile
import unittest
from pathlib import Path

from build_image_review_sheet import build_sheet
from extract_textbook import extract


class ReviewSheetTests(unittest.TestCase):
    def test_generates_local_sheet_without_overwriting_decisions(self):
        import fitz
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "sample.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Image-related airway assessment")
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 12, 12), False)
            page.insert_image(fitz.Rect(100, 120, 160, 180), pixmap=pix)
            doc.save(pdf)
            doc.close()
            owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
            index = root / "index"
            extract(pdf, index, owner, owner + "/sample.pdf")
            out = root / "private"
            result = build_sheet(pdf, index, out, limit=1)
            self.assertEqual(result["rendered"], 1)
            self.assertIn("PDF page 1", (out / "index.html").read_text())
            self.assertEqual(len(list((out / "previews").glob("*.png"))), 1)
            review = json.loads((out / "review.json").read_text())
            self.assertEqual(review["decisions"][0]["decision"], "pending")
            review["decisions"][0]["decision"] = "relevant"
            (out / "review.json").write_text(json.dumps(review))
            build_sheet(pdf, index, out, limit=1)
            self.assertEqual(json.loads((out / "review.json").read_text())["decisions"][0]["decision"], "relevant")

    def test_invalid_limit(self):
        with self.assertRaisesRegex(ValueError, "limit"):
            build_sheet("unused.pdf", "unused", "unused", limit=0)
