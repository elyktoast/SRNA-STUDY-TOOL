import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_blind_review_staging_schema_v2 import preflight, REQUIRED

class Cursor:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.queries = []
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params=None):
        self.queries.append((sql, params))
        if not sql.lstrip().upper().startswith("SELECT"):
            raise AssertionError("Preflight attempted a write")
    def fetchone(self): return next(self.responses)
    def fetchall(self): return next(self.responses)

class DB:
    def __init__(self, responses): self.cur = Cursor(responses)
    def cursor(self): return self.cur

def responses(*, table=True, rls=True, grants=(False,)*4, columns=None):
    return [("staging", "backend"), ("source_library_staging.blind_review_runs",) if table else (None,),
            list((columns or REQUIRED).items()), (rls,), grants]

class PreflightTests(unittest.TestCase):
    def test_missing_migration(self):
        db = DB([("staging", "backend"), (None,)])
        self.assertEqual(preflight(db)["reason"], "migration_not_applied")
    def test_ready_schema(self):
        db = DB(responses())
        self.assertTrue(preflight(db)["ready"])
        self.assertTrue(all(q[0].lstrip().upper().startswith("SELECT") for q in db.cur.queries))
    def test_rejects_client_grants(self):
        db = DB(responses(grants=(True, False, False, False)))
        self.assertIn("client_table_privilege_present", preflight(db)["issues"])
    def test_rejects_missing_rls_or_column(self):
        db = DB(responses(rls=False, columns={k:v for k,v in REQUIRED.items() if k != "owner_uid"}))
        issues = preflight(db)["issues"]
        self.assertIn("rls_not_enabled", issues)
        self.assertIn("column_mismatch:owner_uid", issues)

if __name__ == "__main__":
    unittest.main()
