"""Real-PDF regression coverage for the trusted page loader.

No R2, database, or production services are accessed.
"""
import hashlib
import unittest

import fitz

from source_review_page_loader_v2 import load_verified_review_page

OWNER = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = OWNER + "/integration-fixture.pdf"


def make_pdf():
    doc = fitz.open()
    for text in ("First physical page", "Second physical page"):
        page = doc.new_page(width=360, height=480)
        page.insert_text((48, 60), text)
    data = doc.tobytes()
    doc.close()
    return data


class RealPdfPageLoaderTests(unittest.TestCase):
    def setUp(self):
        self.source = make_pdf()
        self.manifest = {
            "owner_uid": OWNER,
            "r2_key": KEY,
            "sha256": hashlib.sha256(self.source).hexdigest(),
            "pdf_page_count": 2,
        }
        self.source_reads = 0

    def load(self, page=2, source=None):
        def source_loader(owner, key):
            self.assertEqual((owner, key), (OWNER, KEY))
            self.source_reads += 1
            return self.source if source is None else source

        return load_verified_review_page(
            owner_uid=OWNER, r2_key=KEY, pdf_page=page,
            manifest_loader=lambda owner, key: dict(self.manifest),
            source_loader=source_loader)

    def test_renders_actual_second_page_with_reproducible_digest(self):
        result = self.load()
        self.assertTrue(result["png"].startswith(bytes.fromhex("89504e470d0a1a0a")))
        self.assertEqual(hashlib.sha256(result["png"]).hexdigest(), result["image_sha256"])
        self.assertEqual(result["source_sha256"], self.manifest["sha256"])
        self.assertEqual(result["pdf_page"], 2)
        self.assertEqual(self.source_reads, 1)
        with fitz.open(stream=result["png"], filetype="png") as image:
            self.assertEqual(len(image), 1)
            self.assertGreater(image[0].rect.width, 0)
        first = self.load(page=1)
        self.assertNotEqual(first["image_sha256"], result["image_sha256"])

    def test_replaced_source_rejected_even_if_pdf_is_valid(self):
        replacement = fitz.open()
        replacement.new_page().insert_text((50, 50), "Changed source")
        changed = replacement.tobytes()
        replacement.close()
        with self.assertRaisesRegex(ValueError, "changed since review manifest"):
            self.load(source=changed)

    def test_out_of_range_page_fails_before_source_fetch(self):
        with self.assertRaisesRegex(ValueError, "outside trusted manifest"):
            self.load(page=3)
        self.assertEqual(self.source_reads, 0)

    def test_malformed_pdf_does_not_create_an_image(self):
        self.manifest["sha256"] = hashlib.sha256(b"not a PDF").hexdigest()
        with self.assertRaises(Exception):
            self.load(source=b"not a PDF")

    def test_manifest_fingerprint_rejects_uppercase_before_fetch(self):
        self.manifest["sha256"] = self.manifest["sha256"].upper()
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.load()
        self.assertEqual(self.source_reads, 0)


if __name__ == "__main__":
    unittest.main()
