import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_semantic_inventory_reconcile_v2 import load_inventory, reconcile

OWNER = "00000000-0000-4000-8000-000000000001"
HASH = "a" * 64


def connection(pages):
    cur = MagicMock()
    cur.fetchall.side_effect = pages
    conn = MagicMock()
    conn.cursor.return_value.__enter__ = Mock(return_value=cur)
    conn.cursor.return_value.__exit__ = Mock(return_value=False)
    return conn, cur


class ReconcileTests(unittest.TestCase):
    def test_complete_index(self):
        conn, cur = connection([[("a", HASH, [1.0, 0.0]), ("b", HASH, [1.0, 0.0])]])
        result = reconcile(conn, owner_uid=OWNER, embedding_model="test",
                           inventory={"a": HASH, "b": HASH})
        self.assertTrue(result["ready"])
        self.assertEqual(result["expected_count"], 2)
        self.assertEqual(result["missing_count"], 0)
        self.assertEqual(cur.execute.call_args.args[1], (OWNER, "test", "", 1000))

    def test_missing_extra_and_stale_fail_closed(self):
        conn, _ = connection([[("a", "b" * 64, [1.0, 0.0]), ("extra", HASH, [1.0, 0.0])]])
        result = reconcile(conn, owner_uid=OWNER, embedding_model="test",
                           inventory={"a": HASH, "missing": HASH})
        self.assertFalse(result["ready"])
        self.assertEqual(result["missing_ids"], ["missing"])
        self.assertEqual(result["unexpected_ids"], ["extra"])
        self.assertEqual(result["stale_ids"], ["a"])

    def test_paginated_index(self):
        ids = [str(i).zfill(5) for i in range(1001)]
        conn, cur = connection([
            [(item_id, HASH, [1.0, 0.0]) for item_id in ids[:1000]],
            [(ids[-1], HASH, [1.0, 0.0])],
        ])
        result = reconcile(conn, owner_uid=OWNER, embedding_model="test",
                           inventory={item_id: HASH for item_id in ids})
        self.assertTrue(result["ready"])
        self.assertEqual(cur.execute.call_count, 2)

    def test_full_nine_thousand_item_inventory(self):
        ids = [str(i).zfill(5) for i in range(9000)]
        pages = [
            [(item_id, HASH) for item_id in ids[i:i + 1000]]
            for i in range(0, len(ids), 1000)
        ] + [[]]
        conn, cur = connection(pages)
        result = reconcile(conn, owner_uid=OWNER, embedding_model="test",
                           inventory={item_id: HASH for item_id in ids})
        self.assertTrue(result["ready"])
        self.assertEqual(result["indexed_count"], 9000)
        self.assertEqual(cur.execute.call_count, 10)

    def test_duplicate_or_disordered_page_rejected(self):
        conn, _ = connection([[("b", HASH, [1.0, 0.0]), ("a", HASH, [1.0, 0.0])]])
        with self.assertRaisesRegex(ValueError, "pagination"):
            reconcile(conn, owner_uid=OWNER, embedding_model="test",
                      inventory={"a": HASH, "b": HASH})

    def test_invalid_or_inconsistent_embeddings_fail_closed(self):
        invalid = (None, [], [0.0, 0.0], [float("nan"), 1.0],
                   [float("inf"), 1.0], ["bad", 1.0], [1.0],
                   [1.0] * 4097)
        for vector in invalid:
            with self.subTest(vector=str(vector)[:50]):
                conn, _ = connection([[("a", HASH, vector)]])
                with self.assertRaisesRegex(ValueError, "embedding"):
                    reconcile(conn, owner_uid=OWNER, embedding_model="test",
                              inventory={"a": HASH})
        conn, _ = connection([[("a", HASH, [1.0, 0.0]),
                               ("b", HASH, [1.0, 0.0, 0.0])]])
        with self.assertRaisesRegex(ValueError, "dimensions"):
            reconcile(conn, owner_uid=OWNER, embedding_model="test",
                      inventory={"a": HASH, "b": HASH})

    def test_inventory_digest_verified(self):
        entries = [{"item_id": "a", "stem_hash": HASH}]
        digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventory.json"
            path.write_text(json.dumps({"schema_version": 1, "item_count": 1,
                                        "inventory_digest": digest, "entries": entries}))
            inventory, actual = load_inventory(path)
            self.assertEqual(inventory, {"a": HASH})
            self.assertEqual(actual, digest)
            path.write_text(json.dumps({"schema_version": 1, "item_count": 1,
                                        "inventory_digest": "0" * 64, "entries": entries}))
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                load_inventory(path)


if __name__ == "__main__":
    unittest.main()
