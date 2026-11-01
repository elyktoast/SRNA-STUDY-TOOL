import unittest
from unittest.mock import patch
from source_legacy_provenance_audit_v2 import audit_legacy_source

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "810040fc-da03-4fa5-bcc0-78c25957c325"
KEY = OWNER + "/" + BOOK + ".pdf"


class FakeCursor:
    def __init__(self, record):
        self.record = record
        self.sql = None
        self.args = None
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, args):
        self.sql, self.args = sql, args
    def fetchone(self): return self.record


class FakeDB:
    def __init__(self, record):
        self.cur = FakeCursor(record)
    def cursor(self): return self.cur


class FakeR2:
    def head_object(self, **kwargs):
        return {"ContentLength": 45000}


class AuditTests(unittest.TestCase):
    @patch("source_legacy_provenance_audit_v2.load_staging_review_manifest")
    def test_legacy_record_requires_independent_verification(self, manifest):
        manifest.return_value = {"sha256": "a" * 64, "pdf_page_count": 420}
        conn = FakeDB(("ready", 420, 45000, 595, 0))
        result = audit_legacy_source(conn, FakeR2(), owner_uid=OWNER,
                                     textbook_id=BOOK, r2_key=KEY)
        self.assertTrue(result["source_metadata_consistent"])
        self.assertFalse(result["historical_passage_provenance_verified"])
        self.assertFalse(result["safe_to_backfill_legacy_provenance"])
        self.assertTrue(result["requires_independent_reextraction_or_review"])
        self.assertEqual(conn.cur.args, (BOOK, OWNER, KEY))

    @patch("source_legacy_provenance_audit_v2.load_staging_review_manifest")
    def test_mismatched_pages_does_not_establish_source_metadata(self, manifest):
        manifest.return_value = {"sha256": "a" * 64, "pdf_page_count": 400}
        result = audit_legacy_source(
            FakeDB(("ready", 420, 45000, 595, 0)), FakeR2(),
            owner_uid=OWNER, textbook_id=BOOK, r2_key=KEY)
        self.assertFalse(result["source_metadata_consistent"])

    def test_bad_identity_is_rejected_before_database_access(self):
        class NoDB:
            def cursor(self):
                raise AssertionError("Unexpected DB access")
        with self.assertRaises(ValueError):
            audit_legacy_source(NoDB(), FakeR2(), owner_uid="bad",
                                textbook_id=BOOK, r2_key=KEY)


if __name__ == "__main__":
    unittest.main()
