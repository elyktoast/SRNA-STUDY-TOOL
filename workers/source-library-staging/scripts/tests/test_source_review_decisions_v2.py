import unittest
from source_review_decisions_v2 import record_page_decision

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
MANIFEST = {"owner_uid": UID, "pdf_page_count": 20, "sha256": "a" * 64, "r2_key": UID + "/book.pdf"}

class Auth:
    def get_user(self, token):
        if token != "valid": raise ValueError("invalid token")
        return {"id": UID, "active": True}

class Roles:
    def __init__(self, allowed=True): self.allowed = allowed
    def is_active_admin(self, uid): return self.allowed

class Cursor:
    def __init__(self, affected=1): self.rowcount = affected; self.sql = None; self.args = None
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, args): self.sql, self.args = sql, args

class Connection:
    def __init__(self, affected=1): self.cur = Cursor(affected)
    def cursor(self): return self.cur

def run(conn, manifest=MANIFEST, **kwargs):
    params = dict(pdf_page=2, decision="approved", review_note="Image inspected",
                  page_image_inspected=True, access_token="valid",
                  auth_provider=Auth(), protected_role_store=Roles())
    params.update(kwargs)
    return record_page_decision(conn, manifest, **params)

class DecisionTests(unittest.TestCase):
    def test_approval_blocked_without_trusted_inspection_receipt(self):
        conn = Connection()
        with self.assertRaisesRegex(ValueError, "Approval disabled"):
            run(conn)
        self.assertIsNone(conn.cur.sql)
    def test_rejection(self):
        conn = Connection()
        self.assertEqual(run(conn, decision="rejected"), 1)
        self.assertIn("rejected", conn.cur.args)
    def test_revocation(self):
        conn = Connection()
        self.assertEqual(run(conn, decision="revoked"), 1)
        self.assertIn("UPDATE", conn.cur.sql)
        self.assertIn("decision=", conn.cur.sql)
    def test_revocation_missing_row_rejected(self):
        with self.assertRaises(ValueError):
            run(Connection(0), decision="revoked")
    def test_invalid_inputs_never_write(self):
        cases = [
            (dict(page_image_inspected=False), MANIFEST),
            (dict(pdf_page=0), MANIFEST),
            (dict(pdf_page=21), MANIFEST),
            (dict(pdf_page=True), MANIFEST),
            (dict(decision="invalid"), MANIFEST),
            (dict(review_note=" "), MANIFEST),
            (dict(access_token="expired"), MANIFEST),
            (dict(protected_role_store=Roles(False)), MANIFEST),
            ({}, dict(MANIFEST, owner_uid="d7c8ad4c-673d-4d87-a122-7d9bff4451bc")),
            ({}, dict(MANIFEST, sha256="z" * 64)),
            ({}, dict(MANIFEST, pdf_page_count="20")),
        ]
        for args, manifest in cases:
            with self.subTest(args=args, manifest=manifest):
                conn = Connection()
                with self.assertRaises(ValueError): run(conn, manifest, **args)
                self.assertIsNone(conn.cur.sql)

if __name__ == "__main__":
    unittest.main()
