import unittest
from check_page_review_staging_schema_v2 import preflight

COLUMNS = [
    ("id","uuid"), ("owner_uid","uuid"), ("source_sha256","text"),
    ("r2_key","text"), ("pdf_page","integer"), ("reviewer_uid","uuid"),
    ("decision","text"), ("reviewed_at","timestamp with time zone"),
    ("revoked_at","timestamp with time zone"), ("review_note","text"),
]

class Cursor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.queries = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, query, params=None): self.queries.append((query, params))
    def fetchone(self): return next(self.responses)
    def fetchall(self): return next(self.responses)

class Connection:
    def __init__(self, responses): self.cursor_obj = Cursor(responses)
    def cursor(self): return self.cursor_obj

def connection(columns=COLUMNS, rls=True, grants=(False,)*8, exists=True):
    return Connection([("staging","server"), ("approval_table",) if exists else (None,),
                       columns, (rls,), grants])

class PageApprovalPreflightTests(unittest.TestCase):
    def test_missing_migration_fails_closed(self):
        c = Connection([("staging","server"), (None,)])
        self.assertEqual(preflight(c)["reason"], "migration_not_applied")
    def test_ready_schema(self):
        c = connection()
        self.assertTrue(preflight(c)["ready"])
        self.assertEqual(len(c.cursor_obj.queries[-1][1]), 8)
    def test_missing_column(self):
        self.assertIn("column_mismatch:revoked_at",
                      preflight(connection(columns=COLUMNS[:-2]+COLUMNS[-1:]))["issues"])
    def test_rls_disabled(self):
        self.assertIn("rls_not_enabled", preflight(connection(rls=False))["issues"])
    def test_client_grant(self):
        self.assertIn("client_table_privilege_present",
                      preflight(connection(grants=(False,True)+(False,)*6))["issues"])

if __name__ == "__main__": unittest.main()
