import unittest
from contextlib import nullcontext
from unittest.mock import patch
from register_verified_legacy_source_v2 import register_verified_legacy_source

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "2a589498-aaa4-410f-b51a-00d3ab99eafd"
KEY = OWNER + "/810040fc-da03-4fa5-bcc0-78c25957c325.pdf"
DIGEST = "a" * 64


class Cursor:
    def __init__(self, rows):
        self.rows = iter(rows)
        self.statements = []
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, params): self.statements.append((sql, params))
    def fetchone(self): return next(self.rows)


class Conn:
    def __init__(self, rows): self.cur = Cursor(rows)
    def transaction(self): return nullcontext()
    def cursor(self): return self.cur


class RegistrationTests(unittest.TestCase):
    def setUp(self):
        self.kwargs = dict(owner_uid=OWNER, textbook_id=BOOK, r2_key=KEY,
                           source_sha256=DIGEST, source_size_bytes=40000,
                           pdf_page_count=420, fresh_passages=[{"chunk_index": 0,
                           "page_start": 1, "page_end": 1, "content": "Test passage"}],
                           verified_r2_attestation=True, extraction_ocr_enabled=True,
                           explicit_operator_approval=True)

    def test_no_write_without_verified_operator_approval(self):
        class NoDB:
            def transaction(self): raise AssertionError("DB must not be accessed")
        for change in ({"explicit_operator_approval": False},
                       {"verified_r2_attestation": False},
                       {"extraction_ocr_enabled": False}):
            with self.subTest(change=change), self.assertRaises(PermissionError):
                register_verified_legacy_source(NoDB(), **{**self.kwargs, **change})

    @patch("register_verified_legacy_source_v2.compare_indexed_passages")
    def test_persists_provenance_only_after_exact_match(self, compare):
        compare.return_value = dict(same_ordered_passages_and_pages=True,
                                    indexed_passage_count=1, fresh_passage_count=1,
                                    indexed_only_fingerprints=0, fresh_only_fingerprints=0)
        conn = Conn([(KEY, 40000, 420, "ready"), (0,), (BOOK,)])
        result = register_verified_legacy_source(conn, **self.kwargs)
        self.assertTrue(result["source_version_registered"])
        self.assertFalse(result["chapter_citations_approved"])
        self.assertEqual(sum("INSERT INTO" in sql for sql, _ in conn.cur.statements), 1)

    @patch("register_verified_legacy_source_v2.compare_indexed_passages")
    def test_mismatched_passages_never_insert_provenance(self, compare):
        compare.return_value = dict(same_ordered_passages_and_pages=False,
                                    indexed_passage_count=2, fresh_passage_count=1,
                                    indexed_only_fingerprints=1, fresh_only_fingerprints=0)
        conn = Conn([(KEY, 40000, 420, "ready"), (0,)])
        with self.assertRaisesRegex(ValueError, "does not exactly match"):
            register_verified_legacy_source(conn, **self.kwargs)
        self.assertFalse(any("INSERT INTO" in sql for sql, _ in conn.cur.statements))

    def test_mismatched_book_metadata_never_inserts(self):
        conn = Conn([(KEY, 40001, 420, "ready")])
        with self.assertRaises(ValueError):
            register_verified_legacy_source(conn, **self.kwargs)
        self.assertFalse(any("INSERT INTO" in sql for sql, _ in conn.cur.statements))


if __name__ == "__main__":
    unittest.main()
