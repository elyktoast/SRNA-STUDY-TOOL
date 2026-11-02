"""Trusted R2 review-manifest integration and tamper regression tests."""
import hashlib
import io
import json
import unittest

from source_review_manifest_r2_v2 import load_staging_review_manifest

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/fixture.pdf"
QUEUE_KEY = UID + "/_review_queues/fixture.pdf.json"


class Body(io.BytesIO):
    pass


class FakeR2:
    def __init__(self):
        self.pdf = b"%PDF-1.4\\nfixture"
        self.etag = "original"
        self.queue = {"r2_key": KEY, "source_sha256": hashlib.sha256(self.pdf).hexdigest(),
                      "approval_enabled": False, "pdf_page_count": 2,
                      "pages": [{"pdf_page": 1, "review_category": "ocr_error", "characters": 0}]}
        self.attestation = None
        self.bodies = []

    def head_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks" and Key == KEY
        return {"ContentLength": len(self.pdf), "ETag": self.etag}

    def get_object(self, *, Bucket, Key):
        assert Bucket == "srna-staging-textbooks"
        encoded = json.dumps(self.queue).encode()
        att = self.attestation or {"schema_version": 1, "r2_key": KEY,
              "source_sha256": hashlib.sha256(self.pdf).hexdigest(),
              "source_etag": "original", "size_bytes": len(self.pdf),
              "queue_sha256": hashlib.sha256(encoded).hexdigest()}
        if Key == QUEUE_KEY:
            body = Body(encoded)
        elif Key == QUEUE_KEY + ".source.json":
            body = Body(json.dumps(att).encode())
        else:
            raise AssertionError("Unexpected R2 key")
        self.bodies.append(body)
        return {"Body": body}


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.r2 = FakeR2()

    def load(self):
        return load_staging_review_manifest(self.r2, owner_uid=UID, r2_key=KEY)

    def test_valid_manifest_is_derived_from_server_storage(self):
        result = self.load()
        self.assertEqual(result["sha256"], hashlib.sha256(self.r2.pdf).hexdigest())
        self.assertEqual(result["pdf_page_count"], 2)
        self.assertEqual(result["owner_uid"], UID)
        self.assertTrue(all(body.closed for body in self.r2.bodies))

    def test_manifest_key_accepts_valid_pdf_and_rejects_non_pdf(self):
        self.assertEqual(self.load()["r2_key"], KEY)
        for key in (UID + "/fixtureXpdf", UID + "/fixture\\\\.pdf", UID + "/nested/fixture.pdf"):
            with self.subTest(key=key):
                with self.assertRaisesRegex(ValueError, "owner-scoped"):
                    load_staging_review_manifest(self.r2, owner_uid=UID, r2_key=key)

    def test_foreign_owner_rejected_before_storage(self):
        with self.assertRaisesRegex(ValueError, "owner-scoped"):
            load_staging_review_manifest(self.r2, owner_uid="00000000-0000-4000-8000-000000000000", r2_key=KEY)
        self.assertEqual(self.r2.bodies, [])

    def test_tampered_queue_rejected(self):
        self.r2.queue["pages"][0]["characters"] = -1
        with self.assertRaisesRegex(ValueError, "Invalid review queue page"):
            self.load()

    def test_duplicate_pages_rejected(self):
        self.r2.queue["pages"].append(dict(self.r2.queue["pages"][0]))
        with self.assertRaisesRegex(ValueError, "Invalid review queue page"):
            self.load()

    def test_source_replacement_rejected(self):
        self.r2.etag = "replacement"
        with self.assertRaisesRegex(ValueError, "Source attestation mismatch"):
            self.load()

    def test_attestation_digest_mismatch_rejected(self):
        self.r2.attestation = {"schema_version": 1, "r2_key": KEY,
              "source_sha256": hashlib.sha256(self.r2.pdf).hexdigest(),
              "source_etag": "original", "size_bytes": len(self.r2.pdf),
              "queue_sha256": "0" * 64}
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            self.load()

    def test_unapproved_queue_required(self):
        self.r2.queue["approval_enabled"] = True
        with self.assertRaisesRegex(ValueError, "source mismatch"):
            self.load()


if __name__ == "__main__":
    unittest.main()
