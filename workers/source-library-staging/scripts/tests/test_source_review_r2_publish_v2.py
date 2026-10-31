import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from source_review_r2_publish_v2 import publish_verified_queue

UID = "123e4567-e89b-42d3-a456-426614174000"
KEY = UID + "/book.pdf"
BUCKET = "srna-staging-textbooks"


class MissingObject(Exception):
    response = {"Error": {"Code": "404"}}


class Body:
    def __init__(self, data):
        self.data = data
    def iter_chunks(self, chunk_size):
        yield self.data[:8]
        yield self.data[8:]
    def close(self):
        pass


class FakeR2:
    def __init__(self, data):
        self.data = data
        self.etag = "etag-original"
        self.writes = {}
        self.replace_before_publish = False
    def head_object(self, Bucket, Key):
        if Key != KEY:
            if Key not in self.writes:
                raise MissingObject()
            return {"ContentLength": len(self.writes[Key]), "ETag": "stored"}
        if self.replace_before_publish and self.writes is not None:
            self.etag = "etag-replaced"
        return {"ContentLength": len(self.data), "ETag": self.etag}
    def get_object(self, Bucket, Key):
        return {"Body": Body(self.data)}
    def delete_object(self, Bucket, Key):
        self.writes.pop(Key, None)
    def put_object(self, Bucket, Key, Body, ContentType):
        self.writes[Key] = Body


class HeldLock:
    def assert_held(self, key):
        if key != KEY:
            raise ValueError("Unexpected lock scope")


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = b"%PDF-1.4\noriginal"
        self.manifest = {
            "schema_version": 1, "filename": "book.pdf", "owner_uid": UID,
            "r2_key": KEY, "size_bytes": len(self.data),
            "sha256": hashlib.sha256(self.data).hexdigest(),
            "pdf_page_count": 2, "status": "extracted_not_indexed",
            "citation_verified": False, "low_text_pages": [2],
            "low_text_details": [{"pdf_page": 2, "review_category": "ocr_error",
                                  "characters": 0, "ocr_failed": True}],
        }
        (self.root / "manifest.json").write_text(json.dumps(self.manifest))

    def test_apply_without_exclusive_lock_is_rejected(self):
        r2 = FakeR2(self.data)
        with self.assertRaisesRegex(ValueError, "exclusive publication lock"):
            publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True)
        self.assertEqual(r2.writes, {})

    def test_dry_run_has_no_writes(self):
        r2 = FakeR2(self.data)
        result = publish_verified_queue(r2, BUCKET, KEY, self.root)
        self.assertFalse(result["published"])
        self.assertEqual(r2.writes, {})

    def test_apply_publishes_queue_and_attestation(self):
        r2 = FakeR2(self.data)
        result = publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertTrue(result["published"])
        queue = json.loads(r2.writes[result["queue_r2_key"]])
        attestation = json.loads(r2.writes[result["attestation_r2_key"]])
        self.assertEqual(queue["source_sha256"], self.manifest["sha256"])
        self.assertEqual(attestation["source_etag"], "etag-original")
        self.assertFalse(queue["approval_enabled"])

    def test_existing_publication_is_not_overwritten(self):
        r2 = FakeR2(self.data)
        first = publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        snapshot = dict(r2.writes)
        with self.assertRaisesRegex(ValueError, "already published"):
            publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertEqual(snapshot, r2.writes)
        self.assertIn(first["attestation_r2_key"], r2.writes)

    def test_rejects_modified_r2_bytes_without_writes(self):
        r2 = FakeR2(b"%PDF-1.4\nmodified")
        with self.assertRaises(ValueError):
            publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertEqual(r2.writes, {})

    def test_rejects_changed_object_before_publication(self):
        class ChangedR2(FakeR2):
            calls = 0
            def head_object(self, **kwargs):
                self.calls += 1
                result = super().head_object(**kwargs)
                if self.calls == 2:
                    result["ETag"] = "new-etag"
                return result
        r2 = ChangedR2(self.data)
        with self.assertRaisesRegex(ValueError, "changed before publication"):
            publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertEqual(r2.writes, {})

    def test_replacement_after_queue_write_does_not_publish_attestation(self):
        class ReplacedDuringWrite(FakeR2):
            def put_object(self, Bucket, Key, Body, ContentType):
                super().put_object(Bucket=Bucket, Key=Key, Body=Body, ContentType=ContentType)
                if Key.endswith("book.pdf.json"):
                    self.etag = "etag-replaced"
        r2 = ReplacedDuringWrite(self.data)
        with self.assertRaisesRegex(ValueError, "changed during publication"):
            publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertFalse(any(k.endswith(".source.json") for k in r2.writes))

    def test_interrupted_publication_leaves_no_attestation(self):
        class FailingR2(FakeR2):
            def put_object(self, Bucket, Key, Body, ContentType):
                if Key.endswith(".source.json"):
                    raise RuntimeError("simulated attestation failure")
                super().put_object(Bucket=Bucket, Key=Key, Body=Body, ContentType=ContentType)
        r2 = FailingR2(self.data)
        old_key = UID + "/_review_queues/book.pdf.json.source.json"
        r2.writes[old_key] = b"old attestation"
        with self.assertRaisesRegex(RuntimeError, "simulated"):
            publish_verified_queue(r2, BUCKET, KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertNotIn(old_key, r2.writes)

    def test_rejects_nonstaging_bucket(self):
        r2 = FakeR2(self.data)
        with self.assertRaises(ValueError):
            publish_verified_queue(r2, "production-bucket", KEY, self.root, apply=True, publication_lock=HeldLock())
        self.assertEqual(r2.writes, {})


if __name__ == "__main__":
    unittest.main()
