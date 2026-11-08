import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_semantic_index_v2 import prepare, apply, main, validate_staging_db_url

OWNER = "00000000-0000-4000-8000-000000000001"
HASH = "a" * 64


class OfflineImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.inventory = Path(self.temp.name) / "inventory.json"
        self.vectors = Path(self.temp.name) / "vectors.json"
        entries = [{"item_id": "a", "stem_hash": HASH},
                   {"item_id": "b", "stem_hash": HASH}]
        self.digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
        self.inventory.write_text(json.dumps({"schema_version": 1, "item_count": 2,
                                              "inventory_digest": self.digest, "entries": entries}))
        self.bundle = {"schema_version": 1, "inventory_digest": self.digest,
                       "embedding_model": "test-model", "entries": [
                           {"item_id": "a", "stem_hash": HASH, "embedding": [1.0, 0.0]},
                           {"item_id": "b", "stem_hash": HASH, "embedding": [0.0, 1.0]}]}
        self.save()

    def save(self):
        self.vectors.write_text(json.dumps(self.bundle))

    def test_valid_complete_bundle(self):
        rows, inventory, digest, dim = prepare(self.inventory, self.vectors, model="test-model")
        self.assertEqual(len(rows), 2)
        self.assertEqual(dim, 2)
        self.assertEqual(set(inventory), {"a", "b"})
        self.assertEqual(digest, self.digest)

    def test_rejects_missing_extra_stale_duplicate_or_wrong_model(self):
        variants = [
            lambda b: b["entries"].pop(),
            lambda b: b["entries"][0].update(stem_hash="b" * 64),
            lambda b: b["entries"][0].update(item_id="unexpected"),
            lambda b: b["entries"][0].update(item_id="b"),
            lambda b: b.update(embedding_model="other"),
            lambda b: b.update(inventory_digest="0" * 64),
        ]
        for change in variants:
            with self.subTest(change=change):
                self.setUp_bundle()
                change(self.bundle)
                self.save()
                with self.assertRaises(ValueError):
                    prepare(self.inventory, self.vectors, model="test-model")

    def setUp_bundle(self):
        self.bundle = {"schema_version": 1, "inventory_digest": self.digest,
                       "embedding_model": "test-model", "entries": [
                           {"item_id": "a", "stem_hash": HASH, "embedding": [1.0, 0.0]},
                           {"item_id": "b", "stem_hash": HASH, "embedding": [0.0, 1.0]}]}

    def test_rejects_bad_vectors(self):
        for vector in ([], [0, 0], [float("nan"), 1], [1e308, 1],
                       [1], ["1", 2], [1] * 4097):
            with self.subTest(vector=str(vector)[:30]):
                self.setUp_bundle()
                self.bundle["entries"][0]["embedding"] = vector
                self.save()
                with self.assertRaises(ValueError):
                    prepare(self.inventory, self.vectors, model="test-model")
        self.setUp_bundle()
        self.bundle["entries"][0]["embedding"] = [1, 0, 0]
        self.save()
        with self.assertRaisesRegex(ValueError, "dimensions"):
            prepare(self.inventory, self.vectors, model="test-model")

    def test_dry_run_never_connects(self):
        conn = Mock()
        env = {"STAGING_ONLY": "true", "SEMANTIC_INDEX_EMBEDDING_MODEL": "test-model"}
        self.assertEqual(main([str(self.inventory), str(self.vectors)], env, conn), 0)
        conn.assert_not_called()
        self.assertEqual(main([str(self.inventory), str(self.vectors), "--apply"], env, conn), 2)
        conn.assert_not_called()

    def test_staging_database_host_guard(self):
        valid = ("postgresql://postgres:secret@db.xqyasyambwdyhsjkftqu.supabase.co/postgres",
                 "postgresql://postgres.xqyasyambwdyhsjkftqu:secret@aws-0-us-east-1.pooler.supabase.com/postgres")
        for url in valid:
            self.assertTrue(validate_staging_db_url(url))
        for url in ("postgresql://postgres:secret@db.other.supabase.co/postgres",
                    "postgresql://postgres:secret@localhost/postgres",
                    "postgresql://postgres.other:secret@aws-0-us-east-1.pooler.supabase.com/postgres"):
            with self.assertRaises(ValueError):
                validate_staging_db_url(url)

    def test_apply_uses_scoped_upsert_and_verifies_before_commit(self):
        rows, inventory, _, _ = prepare(self.inventory, self.vectors, model="test-model")
        conn = MagicMock()
        cur = MagicMock()
        conn.cursor.return_value.__enter__ = Mock(return_value=cur)
        conn.cursor.return_value.__exit__ = Mock(return_value=False)
        cur.fetchall.return_value = [("a", HASH, [1.0, 0.0]), ("b", HASH, [0.0, 1.0])]
        result = apply(conn, owner_uid=OWNER, model="test-model", rows=rows, inventory=inventory)
        self.assertTrue(result["ready"])
        queries = [call.args[0] for call in cur.execute.call_args_list]
        self.assertEqual(sum("insert into" in q for q in queries), 2)
        self.assertTrue(all("owner_uid=excluded.owner_uid" in q
                            for q in queries if "insert into" in q))
        self.assertTrue(any("select item_id, stem_hash, embedding" in q for q in queries))


if __name__ == "__main__":
    unittest.main()
