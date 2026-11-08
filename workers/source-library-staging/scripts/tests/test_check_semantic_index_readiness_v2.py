import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_semantic_index_readiness_v2 import check, main

OWNER = "00000000-0000-4000-8000-000000000001"
HASH = "a" * 64
ENV = {"STAGING_ONLY": "true", "STAGING_DATABASE_URL": "postgresql://test",
       "SEMANTIC_INDEX_OWNER_UID": OWNER, "SEMANTIC_INDEX_EMBEDDING_MODEL": "test"}


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "inventory.json"
        entries = [{"item_id": "a", "stem_hash": HASH}]
        digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
        self.path.write_text(json.dumps({"schema_version": 1, "inventory_digest": digest,
                                         "item_count": 1, "entries": entries}))

    def connect(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = Mock(return_value=cur)
        conn.cursor.return_value.__exit__ = Mock(return_value=False)
        db = MagicMock()
        db.return_value.__enter__ = Mock(return_value=conn)
        db.return_value.__exit__ = Mock(return_value=False)
        return db

    def test_complete_index_ready(self):
        result = check(inventory_path=self.path, env=ENV,
                       connect=self.connect([("a", HASH, [1.0, 0.0])]))
        self.assertTrue(result["ready"])
        self.assertEqual(result["expected_count"], 1)
        self.assertNotIn("missing_ids", result)

    def test_missing_and_stale_not_ready(self):
        for rows in ([], [("a", "b" * 64, [1.0, 0.0])]):
            with self.subTest(rows=rows):
                result = check(inventory_path=self.path, env=ENV,
                               connect=self.connect(rows))
                self.assertFalse(result["ready"])

    def test_disabled_environment_rejected_before_db(self):
        db = Mock()
        with self.assertRaisesRegex(ValueError, "Staging-only"):
            check(inventory_path=self.path, env={**ENV, "STAGING_ONLY": "false"},
                  connect=db)
        db.assert_not_called()

    def test_exit_codes_fail_closed(self):
        self.assertEqual(main([str(self.path)], ENV, self.connect([])), 1)
        self.assertEqual(main([str(self.path)], ENV, self.connect([("a", HASH, [1.0, 0.0])])), 0)
        self.assertEqual(main([str(self.path)], {}, self.connect([])), 2)


if __name__ == "__main__":
    unittest.main()
