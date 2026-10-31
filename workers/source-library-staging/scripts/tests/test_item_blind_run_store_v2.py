import sqlite3
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_blind_attestation_v2 import sign
from item_blind_run_store_v2 import initialize, register, consume

SECRET = b"unit-test-only-secret-at-least-thirty-two-bytes"
def screening():
    return {"stages": {name: {"status": "pass", "issues": []} for name in
            ("schema", "deterministic_text", "math", "evidence", "duplicates", "blind_model", "human_review")},
            "can_publish": False}
def signed():
    return sign(item_id="q1", run_id="r1", secret=SECRET,
                result={"status": "pass", "issues": [], "generator_model_id": "a",
                        "reviewer_model_id": "b", "human_review_required": True,
                        "can_publish": False})
class RunStoreTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        initialize(self.conn)
    def tearDown(self):
        self.conn.close()
    def test_consumes_once(self):
        register(self.conn, run_id="r1", item_id="q1")
        first = consume(self.conn, screening(), signed(), item_id="q1", run_id="r1", secret=SECRET)
        self.assertFalse(first["can_publish"])
        with self.assertRaises(ValueError):
            consume(self.conn, screening(), signed(), item_id="q1", run_id="r1", secret=SECRET)
    def test_unknown_run_rejected(self):
        with self.assertRaises(ValueError):
            consume(self.conn, screening(), signed(), item_id="q1", run_id="r1", secret=SECRET)
    def test_tamper_does_not_consume(self):
        register(self.conn, run_id="r1", item_id="q1")
        forged = signed()
        forged["result"]["status"] = "flag"
        with self.assertRaises(ValueError):
            consume(self.conn, screening(), forged, item_id="q1", run_id="r1", secret=SECRET)
        self.assertEqual(self.conn.execute("SELECT state FROM blind_review_runs").fetchone()[0], "pending")
    def test_duplicate_registration_rejected(self):
        register(self.conn, run_id="r1", item_id="q1")
        with self.assertRaises(sqlite3.IntegrityError):
            register(self.conn, run_id="r1", item_id="q1")

if __name__ == "__main__":
    unittest.main()
