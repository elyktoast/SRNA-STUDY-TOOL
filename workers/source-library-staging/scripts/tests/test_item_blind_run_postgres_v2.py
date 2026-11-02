import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_blind_attestation_v2 import sign
from item_blind_run_postgres_v2 import register, consume

SECRET = b"test-only-32-byte-signing-secret-for-tests"
OWNER = "00000000-0000-4000-8000-000000000001"
def report():
    return {"stages": {name: {"status": "pass", "issues": []} for name in
            ("schema", "deterministic_text", "math", "evidence", "duplicates", "blind_model", "human_review")},
            "can_publish": False}
def signed():
    return sign(item_id="q1", run_id="r1", secret=SECRET,
                result={"status": "pass", "issues": [], "generator_model_id": "a",
                        "reviewer_model_id": "b", "human_review_required": True, "can_publish": False})
class FakeCursor:
    def __init__(self, db): self.db = db
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def execute(self, sql, params):
        self.db.queries.append((sql, params))
        if sql.startswith("INSERT"):
            if self.db.exists: raise ValueError("Duplicate")
            self.db.exists = True
        elif sql.startswith("UPDATE"):
            self.db.claimed = self.db.exists and not self.db.consumed and params[1] == "r1" and params[2] == "q1" and params[3] == OWNER
            if self.db.claimed: self.db.consumed = True
    def fetchone(self): return ("r1",) if self.db.claimed else None
class FakeDB:
    def __init__(self):
        self.exists = self.consumed = self.claimed = False
        self.commits = self.rollbacks = 0
        self.queries = []
    def cursor(self): return FakeCursor(self)
    def commit(self): self.commits += 1
    def rollback(self): self.rollbacks += 1

class PostgresRunTests(unittest.TestCase):
    def test_owner_scoped_atomic_claim_and_replay(self):
        db = FakeDB()
        register(db, run_id="r1", item_id="q1", owner_uid=OWNER)
        first = consume(db, report(), signed(), item_id="q1", run_id="r1", owner_uid=OWNER, secret=SECRET)
        self.assertFalse(first["can_publish"])
        self.assertIn("state='pending'", db.queries[-1][0])
        self.assertIn("owner_uid=%s", db.queries[-1][0])
        with self.assertRaises(ValueError):
            consume(db, report(), signed(), item_id="q1", run_id="r1", owner_uid=OWNER, secret=SECRET)
        self.assertEqual(db.rollbacks, 1)
    def test_wrong_owner_rejected(self):
        db = FakeDB()
        register(db, run_id="r1", item_id="q1", owner_uid=OWNER)
        with self.assertRaises(ValueError):
            consume(db, report(), signed(), item_id="q1", run_id="r1",
                    owner_uid="00000000-0000-4000-8000-000000000002", secret=SECRET)
        self.assertEqual(db.commits, 1)
    def test_tampered_signature_never_queries_database(self):
        db = FakeDB()
        forged = signed()
        forged["result"]["status"] = "flag"
        with self.assertRaises(ValueError):
            consume(db, report(), forged, item_id="q1", run_id="r1", owner_uid=OWNER, secret=SECRET)
        self.assertEqual(db.queries, [])
    def test_registration_is_owner_scoped(self):
        db = FakeDB()
        register(db, run_id="r1", item_id="q1", owner_uid=OWNER)
        self.assertEqual(db.queries[0][1], ("r1", "q1", OWNER))

if __name__ == "__main__":
    unittest.main()
