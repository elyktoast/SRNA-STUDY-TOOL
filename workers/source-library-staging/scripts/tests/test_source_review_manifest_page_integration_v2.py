"""Real PDF integration: attested staging queue -> trusted R2 source -> rendered PNG."""
import hashlib
import io
import json
import unittest

from source_review_manifest_r2_v2 import load_staging_review_manifest
from source_review_page_loader_v2 import load_verified_review_page
from source_review_r2_loader_v2 import fetch_verified_staging_pdf

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/integration.pdf"
QUEUE = UID + "/_review_queues/integration.pdf.json"


class Body(io.BytesIO):
    def iter_chunks(self, chunk_size):
        while True:
            chunk = self.read(chunk_size)
            if not chunk:
                return
            yield chunk


class R2:
    def __init__(self, pdf):
        self.pdf = pdf
        self.etag = "original"
        self.queue = {"r2_key": KEY, "source_sha256": hashlib.sha256(pdf).hexdigest(),
                      "approval_enabled": False, "pdf_page_count": 2,
                      "pages": [{"pdf_page": 2, "review_category": "ocr_error", "characters": 0}]}
        self.queue_override = None
        self.pdf_override = None
        self.bodies = []
        self.requested_keys = []

    def head_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks" and Key == KEY
        return {"ContentLength": len(self.pdf), "ETag": self.etag}

    def get_object(self, *, Bucket, Key):
        self.requested_keys.append(Key)
        queue_bytes = json.dumps(self.queue).encode()
        if Key == QUEUE:
            data = self.queue_override if self.queue_override is not None else queue_bytes
        elif Key == QUEUE + ".source.json":
            data = json.dumps({"schema_version": 1, "r2_key": KEY,
                "source_sha256": hashlib.sha256(self.pdf).hexdigest(),
                "source_etag": "original", "size_bytes": len(self.pdf),
                "queue_sha256": hashlib.sha256(queue_bytes).hexdigest()}).encode()
        elif Key == KEY:
            data = self.pdf_override if self.pdf_override is not None else self.pdf
        else:
            raise AssertionError("Unexpected key")
        body = Body(data)
        self.bodies.append(body)
        return {"Body": body, "ContentLength": len(data), "ETag": self.etag}


class ManifestPageIntegrationTests(unittest.TestCase):
    def setUp(self):
        import fitz
        doc = fitz.open()
        for text in ("First physical page", "Second physical page"):
            page = doc.new_page()
            page.insert_text((72, 72), text)
        self.pdf = doc.tobytes()
        doc.close()
        self.r2 = R2(self.pdf)

    def render(self, page=2):
        def manifest_loader(owner, key):
            return load_staging_review_manifest(self.r2, owner_uid=owner, r2_key=key)
        def source_loader(owner, key):
            return fetch_verified_staging_pdf(self.r2, owner_uid=owner, r2_key=key,
                                               expected_sha256=hashlib.sha256(self.pdf).hexdigest())
        return load_verified_review_page(owner_uid=UID, r2_key=KEY, pdf_page=page,
                                         manifest_loader=manifest_loader, source_loader=source_loader)

    def test_attested_real_pdf_page_rendered_and_closed(self):
        result = self.render()
        self.assertEqual(result["pdf_page"], 2)
        self.assertEqual(result["source_sha256"], hashlib.sha256(self.pdf).hexdigest())
        self.assertTrue(result["png"].startswith(bytes([137,80,78,71,13,10,26,10])))
        self.assertEqual(result["image_sha256"], hashlib.sha256(result["png"]).hexdigest())
        self.assertTrue(all(body.closed for body in self.r2.bodies))

    def test_attested_pages_render_distinct_images(self):
        self.assertNotEqual(self.render(1)["image_sha256"], self.render(2)["image_sha256"])

    def test_queue_tampering_fails_before_pdf_fetch(self):
        self.r2.queue_override = b'{"tampered":true}'
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            self.render()
        self.assertNotIn(KEY, self.r2.requested_keys)

    def test_source_tampering_fails_before_image(self):
        self.r2.pdf_override = b"%PDF-1.4\\ntampered"
        with self.assertRaisesRegex(ValueError, "response size|fingerprint"):
            self.render()
        self.assertTrue(all(body.closed for body in self.r2.bodies))

    def test_page_outside_manifest_fails_before_pdf_fetch(self):
        with self.assertRaisesRegex(ValueError, "outside trusted manifest"):
            self.render(3)
        self.assertNotIn(KEY, self.r2.requested_keys)


if __name__ == "__main__":
    unittest.main()
