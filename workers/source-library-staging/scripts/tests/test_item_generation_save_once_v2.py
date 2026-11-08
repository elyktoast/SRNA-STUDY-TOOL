"""Unit coverage for checkpoint-to-draft idempotency and failure boundaries."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_checkpoint_store_v2 import save_once

OWNER = "00000000-0000-4000-8000-000000000001"
BOOK = "00000000-0000-4000-8000-000000000002"
DRAFT = "00000000-0000-4000-8000-000000000003"
KEY = {"textbook_id": BOOK, "request_hash": "a"*64, "evidence_hash": "b"*64}

class Cursor:
    def __init__(self, conn):
        self.conn = conn
        self.rowcount = 1
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def execute(self, query, params):
        self.conn.queries.append((query, params))
        if "select c.completed_result" in query:
            self.conn.row = (self.conn.checkpoint,) if self.conn.checkpoint is not None else None
        elif "select d.status" in query:
            self.conn.row = (self.conn.draft_status,) if self.conn.draft_status else None
        elif "update source_library_staging.generation_checkpoints_v2" in query:
            self.rowcount = self.conn.update_count
        else:
            raise AssertionError("Unexpected SQL")
    def fetchone(self):
        return self.conn.row

class Connection:
    def __init__(self, checkpoint, draft_status="pending_review", update_count=1):
        self.checkpoint = checkpoint
        self.draft_status = draft_status
        self.update_count = update_count
        self.commits = 0
        self.queries = []
    def cursor(self):
        return Cursor(self)
    def commit(self):
        self.commits += 1

class SaveOnceTests(unittest.TestCase):
    def test_new_draft_is_linked_and_committed_once(self):
        conn = Connection({"item_id": "test"})
        calls = []
        def saver(db, payload):
            calls.append(payload)
            return {"draft_id": DRAFT, "status": "pending_review"}
        result = save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                           checkpoint_key=KEY, saver=saver)
        self.assertEqual(result["draft_id"], DRAFT)
        self.assertEqual(conn.commits, 1)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["owner_uid"], OWNER)
        self.assertIn("for update of c", conn.queries[0][0].lower())
        self.assertIn("saved_draft", conn.queries[-1][0])

    def test_recovery_returns_existing_without_inserting(self):
        conn = Connection({"saved_draft": {"draft_id": DRAFT}}, draft_status="needs_revision")
        def forbidden(*args):
            raise AssertionError("Duplicate save")
        result = save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                           checkpoint_key=KEY, saver=forbidden)
        self.assertEqual(result, {"draft_id": DRAFT, "status": "needs_revision"})
        self.assertEqual(conn.commits, 0)

    def test_owner_scoped_query_and_missing_checkpoint(self):
        conn = Connection(None)
        with self.assertRaisesRegex(ValueError, "Completed checkpoint unavailable"):
            save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                      checkpoint_key=KEY, saver=lambda *_: None)
        self.assertEqual(conn.queries[0][1][:3], (OWNER, BOOK, OWNER))

    def test_missing_existing_draft_fails_closed(self):
        conn = Connection({"saved_draft": {"draft_id": DRAFT}}, draft_status=None)
        with self.assertRaisesRegex(ValueError, "Previously saved draft unavailable"):
            save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                      checkpoint_key=KEY, saver=lambda *_: None)
        self.assertEqual(conn.commits, 0)

    def test_failed_insert_does_not_commit(self):
        conn = Connection({"item_id": "test"})
        def failure(*args):
            raise RuntimeError("DB insert failure")
        with self.assertRaises(RuntimeError):
            save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                      checkpoint_key=KEY, saver=failure)
        self.assertEqual(conn.commits, 0)

    def test_failed_checkpoint_link_does_not_commit(self):
        conn = Connection({"item_id": "test"}, update_count=0)
        with self.assertRaisesRegex(ValueError, "association failed"):
            save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                      checkpoint_key=KEY,
                      saver=lambda *_: {"draft_id": DRAFT, "status": "pending_review"})
        self.assertEqual(conn.commits, 0)

    def test_mismatched_textbook_rejected_before_sql(self):
        conn = Connection({"item_id": "test"})
        with self.assertRaisesRegex(ValueError, "textbook mismatch"):
            save_once(conn, owner_uid=OWNER,
                      save_payload={"textbook_id": DRAFT}, checkpoint_key=KEY,
                      saver=lambda *_: None)
        self.assertEqual(conn.queries, [])

    def test_invalid_fingerprint_rejected(self):
        conn = Connection({"item_id": "test"})
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            save_once(conn, owner_uid=OWNER, save_payload={"textbook_id": BOOK},
                      checkpoint_key={**KEY, "request_hash": "invalid"},
                      saver=lambda *_: None)
        self.assertEqual(conn.queries, [])

if __name__ == "__main__":
    unittest.main()
