"""Local-only image renderer tests; generated PDFs contain no textbook content."""
import json
import tempfile
import unittest
from pathlib import Path

from extract_textbook import extract
from render_image_asset import render_asset


class RenderImageAssetTests(unittest.TestCase):
    def test_render_and_reject_tampered_geometry(self):
        import fitz
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pdf = root / "sample.pdf"
            doc = fitz.open()
            page = doc.new_page()
            page.insert_text((72, 72), "Image-associated airway assessment passage")
            pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 16, 16), False)
            page.insert_image(fitz.Rect(100, 120, 160, 180), pixmap=pix)
            doc.save(pdf)
            doc.close()
            owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
            index = root / "index"
            extract(pdf, index, owner, owner + "/sample.pdf")
            assets = json.loads((index / "image_assets.json").read_text())
            self.assertEqual(len(assets), 1)
            output = root / "private" / "asset.png"
            render_asset(pdf, index, assets[0]["asset_id"], output)
            self.assertTrue(output.is_file())
            with fitz.open(pdf) as source:
                self.assertGreater(source[0].get_images().__len__(), 0)
            assets[0]["bbox"][0] += 10
            (index / "image_assets.json").write_text(json.dumps(assets))
            with self.assertRaisesRegex(ValueError, "geometry"):
                render_asset(pdf, index, assets[0]["asset_id"], root / "bad.png")
            self.assertFalse((root / "bad.png").exists())

    def test_invalid_asset_id_rejected(self):
        with self.assertRaisesRegex(ValueError, "identifier"):
            render_asset("unused.pdf", "unused", "../invalid", "out.png")
