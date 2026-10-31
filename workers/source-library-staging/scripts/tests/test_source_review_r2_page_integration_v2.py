"""Integration checks for the trusted R2 -> manifest -> page PNG pipeline.

These tests use real PyMuPDF rendering and a fake in-memory R2 client.
They do not exercise reviewer authentication, nonce issuance, or a live endpoint.
"""
import hashlib
import unittest
from unittest.mock import patch

from source_review_page_loader_v2 import load_verified_review_page
from source_review_r2_loader_v2 import fetch_verified_staging_pdf

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/synthetic.pdf"


class Body:
    def __init__(self, data):
        self.data = data
        self.closed = False
    def iter_chunks(self, chunk_size):
        yield self.data
    def close(self):
        self.closed = True


class FakeR2:
    def __init__(self, pdf):
        self.pdf = pdf
        self.etag = "original"
        self.replace_on_read = False
        self.body = None
    def head_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks" and Key == KEY
        return {"ContentLength": len(self.pdf), "ETag": self.etag}
    def get_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks" and Key == KEY
        self.body = Body(self.pdf)
        if self.replace_on_read:
            self.etag = "replacement"
        return {"Body": self.body}


class R2PageIntegrationTests(unittest.TestCase):
    def setUp(self):
        import fitz
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((72, 72), "Synthetic staging PDF page inspection")
        self.pdf = doc.tobytes()
        doc.close()
        self.sha = hashlib.sha256(self.pdf).hexdigest()
        self.r2 = FakeR2(self.pdf)

    def render(self, manifest=None):
        metadata = manifest or {
            "owner_uid": UID, "r2_key": KEY,
            "sha256": self.sha, "pdf_page_count": 1}
        return load_verified_review_page(
            owner_uid=UID, r2_key=KEY, pdf_page=1,
            manifest_loader=lambda *_: metadata,
            source_loader=lambda owner, key: fetch_verified_staging_pdf(
                self.r2, owner_uid=owner, r2_key=key,
                expected_sha256=metadata["sha256"]))

    def test_real_pdf_render_from_verified_r2(self):
        result = self.render()
        self.assertTrue(result["png"].startswith(b"\\x89PNG\\r\\n\\x1a\\n"))
        self.assertEqual(result["image_sha256"], hashlib.sha256(result["png"]).hexdigest())
        self.assertEqual(result["source_sha256"], self.sha)
        self.assertTrue(self.r2.body.closed)

    def test_tampered_manifest_fails_before_r2(self):
        with self.assertRaisesRegex(ValueError, "identity mismatch"):
            self.render({"owner_uid": UID, "r2_key": KEY + "-other",
                         "sha256": self.sha, "pdf_page_count": 1})
        self.assertIsNone(self.r2.body)

    def test_source_replacement_fails_before_render(self):
        self.r2.replace_on_read = True
        with self.assertRaisesRegex(ValueError, "replaced"):
            self.render()
        self.assertTrue(self.r2.body.closed)

    def test_manifest_fingerprint_mismatch_fails(self):
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            self.render({"owner_uid": UID, "r2_key": KEY,
                         "sha256": "a" * 64, "pdf_page_count": 1})
        self.assertTrue(self.r2.body.closed)


if __name__ == "__main__":
    unittest.main()
