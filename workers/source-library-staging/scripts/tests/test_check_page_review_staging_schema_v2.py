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

def connection(columns=COLUMNS, rls=True, grants=(False,)*8, exists=True, schema_create=(False,False), force_rls=True, service_bypass=True, service_select=True):
    return Connection([("staging","server"), ("approval_table",) if exists else (None,),
                       columns, (rls, force_rls), grants, schema_create, (service_bypass,), (service_select,)])

class PageApprovalPreflightTests(unittest.TestCase):
    def test_missing_migration_fails_closed(self):
        c = Connection([("staging","server"), (None,)])
        self.assertEqual(preflight(c)["reason"], "migration_not_applied")
    def test_ready_schema(self):
        c = connection()
        self.assertTrue(preflight(c)["ready"])
        self.assertEqual(len(c.cursor_obj.queries[-4][1]), 8)
        self.assertEqual(len(c.cursor_obj.queries[-3][1]), 2)
        self.assertIsNone(c.cursor_obj.queries[-2][1])
        self.assertEqual(len(c.cursor_obj.queries[-1][1]), 1)
    def test_missing_column(self):
        self.assertIn("column_mismatch:revoked_at",
                      preflight(connection(columns=COLUMNS[:-2]+COLUMNS[-1:]))["issues"])
    def test_rls_not_forced(self):
        self.assertIn("rls_not_forced", preflight(connection(force_rls=False))["issues"])
    def test_rls_disabled(self):
        self.assertIn("rls_not_enabled", preflight(connection(rls=False))["issues"])
    def test_client_schema_create_grant(self):
        self.assertIn("client_schema_create_privilege_present",
                      preflight(connection(schema_create=(True,False)))["issues"])
    def test_server_role_requires_explicit_access(self):
        self.assertIn("service_role_cannot_bypass_forced_rls",
                      preflight(connection(service_bypass=False))["issues"])
        self.assertIn("service_role_missing_select",
                      preflight(connection(service_select=False))["issues"])
    def test_client_grant(self):
        self.assertIn("client_table_privilege_present",
                      preflight(connection(grants=(False,True)+(False,)*6))["issues"])

if __name__ == "__main__": unittest.main()
