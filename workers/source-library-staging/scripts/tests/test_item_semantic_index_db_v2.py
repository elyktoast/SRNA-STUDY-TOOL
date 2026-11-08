import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, MagicMock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_semantic_index_db_v2 import lookup, MAX_ROWS

OWNER = "00000000-0000-4000-8000-000000000001"

class SemanticIndexTests(unittest.TestCase):
    def connection(self, rows):
        cur = MagicMock()
        cur.fetchall.return_value = rows
        conn = MagicMock()
        conn.cursor.return_value.__enter__ = Mock(return_value=cur)
        conn.cursor.return_value.__exit__ = Mock(return_value=False)
        return conn, cur

    def test_owner_model_scoped_complete_search(self):
        conn, cur = self.connection([("prior-1", [1.0, 0.0])])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0, 0.0], index_ready=True, expected_item_ids={"prior-1", "draft-1"})
        result = callback({"stem": "Clinical stem", "item_id": "draft-1"})
        self.assertTrue(result["search_complete"])
        self.assertEqual(result["neighbors"][0]["item_id"], "prior-1")
        query, params = cur.execute.call_args.args
        self.assertIn("owner_uid=%s", query)
        self.assertIn("embedding_model=%s", query)
        self.assertEqual(params, (OWNER, "test-v1", "draft-1", MAX_ROWS + 1))

    def test_missing_canonical_inventory_rejected(self):
        with self.assertRaisesRegex(ValueError, "canonical item inventory"):
            lookup(Mock(), owner_uid=OWNER, embedding_model="test-v1",
                   embed=lambda stem: [1.0, 0.0], index_ready=True)

    def test_partial_index_never_reports_complete(self):
        conn, _ = self.connection([("prior-1", [1.0, 0.0])])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0, 0.0], index_ready=True,
                          expected_item_ids={"prior-1", "prior-2", "draft-1"})
        with self.assertRaisesRegex(ValueError, "coverage"):
            callback({"stem": "Clinical stem", "item_id": "draft-1"})

    def test_unexpected_index_item_rejected(self):
        conn, _ = self.connection([("untracked", [1.0, 0.0])])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0, 0.0], index_ready=True,
                          expected_item_ids={"prior-1", "draft-1"})
        with self.assertRaisesRegex(ValueError, "coverage"):
            callback({"stem": "Clinical stem", "item_id": "draft-1"})

    def test_missing_candidate_id_rejected(self):
        conn, _ = self.connection([])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0, 0.0], index_ready=True,
                          expected_item_ids={"prior-1"})
        with self.assertRaisesRegex(ValueError, "candidate item ID"):
            callback({"stem": "Clinical stem"})

    def test_wrong_candidate_dimensions_rejected(self):
        conn, _ = self.connection([])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0], index_ready=True,
                          expected_item_ids={"draft-1"})
        with self.assertRaisesRegex(ValueError, "dimensions"):
            callback({"stem": "Clinical stem", "item_id": "draft-1"})

    def test_invalid_indexed_embedding_rejected(self):
        conn, _ = self.connection([("prior-1", None)])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0, 0.0], index_ready=True,
                          expected_item_ids={"prior-1", "draft-1"})
        with self.assertRaisesRegex(ValueError, "indexed embedding"):
            callback({"stem": "Clinical stem", "item_id": "draft-1"})

    def test_unverified_index_rejected(self):
        with self.assertRaises(ValueError):
            lookup(Mock(), owner_uid=OWNER, embedding_model="test-v1",
                   embed=lambda stem: [1.0, 0.0], index_ready=False, expected_item_ids={"prior-1"})

    def test_invalid_embedding_rejected_even_with_empty_index(self):
        conn, _ = self.connection([])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [0.0, 0.0], index_ready=True, expected_item_ids={"prior-1"})
        with self.assertRaises(ValueError):
            callback({"stem": "Clinical stem", "item_id": "draft-1"})

    def test_incomplete_result_rejected(self):
        conn, _ = self.connection([("prior-" + str(i), [1.0, 0.0])
                                   for i in range(MAX_ROWS + 1)])
        callback = lookup(conn, owner_uid=OWNER, embedding_model="test-v1",
                          embed=lambda stem: [1.0, 0.0], index_ready=True, expected_item_ids={"prior-1"})
        with self.assertRaisesRegex(ValueError, "exhaustive"):
            callback({"stem": "Clinical stem"})

if __name__ == "__main__":
    unittest.main()
