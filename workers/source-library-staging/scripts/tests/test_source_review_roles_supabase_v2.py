import unittest
from source_review_roles_supabase_v2 import ProtectedReviewerRoleStore

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"

class Cursor:
    def __init__(self, row):
        self.row = row
        self.calls = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args): self.calls.append((sql, args))
    def fetchone(self): return self.row

class Connection:
    def __init__(self, row):
        self.cur = Cursor(row)
    def cursor(self): return self.cur

class ProtectedRolesTests(unittest.TestCase):
    def test_active_admin(self):
        conn = Connection((True,))
        self.assertTrue(ProtectedReviewerRoleStore(conn).is_active_admin(UID))
        sql, args = conn.cur.calls[0]
        self.assertIn("revoked_at IS NULL", sql)
        self.assertIn("active IS TRUE", sql)
        self.assertEqual(args, (UID,))
    def test_revoked_or_missing_admin(self):
        self.assertFalse(ProtectedReviewerRoleStore(Connection((False,))).is_active_admin(UID))
    def test_missing_or_malformed_result_fails_closed(self):
        for row in (None, ("true",), (1,)):
            with self.subTest(row=row), self.assertRaises(ValueError):
                ProtectedReviewerRoleStore(Connection(row)).is_active_admin(UID)
    def test_invalid_uid_cannot_query(self):
        conn = Connection((True,))
        with self.assertRaises(ValueError):
            ProtectedReviewerRoleStore(conn).is_active_admin("not-a-uuid")
        self.assertEqual(conn.cur.calls, [])
    def test_connection_required(self):
        with self.assertRaises(ValueError):
            ProtectedReviewerRoleStore(None)
    def test_database_failure_fails_closed(self):
        class Broken:
            def cursor(self): raise RuntimeError("database unavailable")
        with self.assertRaises(RuntimeError):
            ProtectedReviewerRoleStore(Broken()).is_active_admin(UID)

if __name__ == "__main__":
    unittest.main()
