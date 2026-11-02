import unittest
from datetime import datetime, timezone
from source_review_nonces_v2 import register_inspection_nonce, consume_inspection_nonce

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
ARGS = dict(nonce="0123456789abcdef0123456789abcdef", reviewer_uid=UID,
            owner_uid=UID, source_sha256="a"*64, r2_key=UID+"/book.pdf", pdf_page=2)

class Cursor:
    def __init__(self, count=1):
        self.rowcount = count
        self.calls = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args): self.calls.append((sql, args))

class Conn:
    def __init__(self, count=1): self.cur = Cursor(count)
    def cursor(self): return self.cur

class NonceTests(unittest.TestCase):
    def test_registration(self):
        conn = Conn()
        digest = register_inspection_nonce(conn, issued_at=1000, **ARGS)
        self.assertEqual(len(digest), 64)
        sql, params = conn.cur.calls[0]
        self.assertIn("INSERT INTO", sql)
        self.assertEqual(params[0], digest)
        self.assertEqual(params[-1], datetime.fromtimestamp(1300, tz=timezone.utc))
    def test_consumption_is_atomic_and_bound(self):
        conn = Conn()
        self.assertTrue(consume_inspection_nonce(conn, **ARGS))
        sql, params = conn.cur.calls[0]
        self.assertIn("consumed_at IS NULL", sql)
        self.assertIn("expires_at > now()", sql)
        self.assertEqual(params[1], UID)
        self.assertEqual(params[-1], 2)
    def test_missing_or_consumed_nonce_fails_closed(self):
        with self.assertRaises(ValueError):
            consume_inspection_nonce(Conn(0), **ARGS)
    def test_invalid_bindings_never_reach_database(self):
        bad = (dict(nonce="wrong"), dict(owner_uid="not-a-uuid"),
               dict(source_sha256="z"*64), dict(r2_key="other/book.pdf"),
               dict(pdf_page=True), dict(pdf_page=0))
        for change in bad:
            with self.subTest(change=change):
                conn = Conn()
                with self.assertRaises(ValueError):
                    consume_inspection_nonce(conn, **dict(ARGS, **change))
                self.assertEqual(conn.cur.calls, [])
    def test_failed_registration(self):
        with self.assertRaises(ValueError):
            register_inspection_nonce(Conn(0), issued_at=1000, **ARGS)

if __name__ == "__main__":
    unittest.main()
