"""Integration contract: extraction and queue publication remain operator-controlled."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from process_r2_textbook import run

UID = "123e4567-e89b-42d3-a456-426614174000"
KEY = UID + "/book.pdf"


class FakeBody:
    def __init__(self, data):
        self.data = data
    def iter_chunks(self, chunk_size):
        yield self.data
    def close(self):
        pass


class FakeR2:
    def __init__(self, data):
        self.data = data
    def head_object(self, Bucket, Key):
        return {"ContentLength": len(self.data), "ETag": "source-etag"}
    def get_object(self, Bucket, Key):
        return {"Body": FakeBody(self.data)}


class R2ReviewIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.data = b"%PDF-1.4\nfixture"
        self.r2 = FakeR2(self.data)

    def fake_process(self, pdf, out, owner_uid, r2_key, **kwargs):
        self.assertEqual(owner_uid, UID)
        self.assertEqual(r2_key, KEY)
        self.assertEqual(kwargs["expected_sha256"], hashlib.sha256(self.data).hexdigest())
        out.mkdir(parents=True, exist_ok=True)
        (out / "manifest.json").write_text(json.dumps({
            "schema_version": 1, "filename": pdf.name, "owner_uid": UID,
            "r2_key": KEY, "size_bytes": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "pdf_page_count": 1, "low_text_pages": [], "low_text_details": [],
            "status": "extracted_not_indexed", "citation_verified": False,
        }))
        return {"passages": 1, "indexed": False}

    def test_dry_run_calls_publisher_without_apply(self):
        with patch("process_r2_textbook.process", side_effect=self.fake_process), \
             patch("process_r2_textbook.publish_verified_queue") as publisher:
            publisher.return_value = {"published": False}
            result = run(UID, KEY, client=self.r2, review_queue_mode="dry-run")
            self.assertEqual(result["review_queue_publication"], {"published": False})
            self.assertFalse(publisher.call_args.kwargs["apply"])

    def test_publication_apply_rejected_until_lock_coordinator_exists(self):
        with self.assertRaisesRegex(ValueError, "exclusive lock coordinator"):
            run(UID, KEY, client=self.r2, review_queue_mode="apply")

    def test_database_apply_cannot_combine_with_publication(self):
        with self.assertRaisesRegex(ValueError, "exclusive lock coordinator"):
            run(UID, KEY, apply=True, client=self.r2, review_queue_mode="apply")

    def test_invalid_mode_rejected(self):
        with self.assertRaisesRegex(ValueError, "mode"):
            run(UID, KEY, client=self.r2, review_queue_mode="automatic")


if __name__ == "__main__":
    unittest.main()
