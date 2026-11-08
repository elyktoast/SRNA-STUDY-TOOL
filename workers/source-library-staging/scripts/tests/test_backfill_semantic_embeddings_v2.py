import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backfill_semantic_embeddings_v2 import backfill, load_source, load_progress


class BackfillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.source = base / "source.json"
        self.progress = base / "progress.jsonl"
        self.output = base / "bundle.json"
        self.entries = []
        stems = []
        for item_id in ("a", "b", "c"):
            stem = "Question " + item_id
            self.entries.append({"item_id": item_id,
                                 "stem_hash": hashlib.sha256(stem.encode()).hexdigest()})
            stems.append({"item_id": item_id, "stem": stem})
        digest = hashlib.sha256(json.dumps(self.entries, separators=(",", ":")).encode()).hexdigest()
        self.source.write_text(json.dumps({"schema_version": 1, "inventory_digest": digest,
                                           "item_count": 3, "entries": self.entries,
                                           "stems": stems}))

    def test_resume_and_complete_without_repeating_calls(self):
        calls = []
        def embed(stem):
            calls.append(stem)
            return [1.0, 0.0]
        first = backfill(self.source, self.progress, self.output, embed=embed, max_new=2)
        self.assertFalse(first["complete"])
        self.assertEqual(first["new_calls"], 2)
        self.assertFalse(self.output.exists())
        second = backfill(self.source, self.progress, self.output, embed=embed, max_new=2)
        self.assertTrue(second["complete"])
        self.assertEqual(second["new_calls"], 1)
        self.assertEqual(len(calls), 3)
        self.assertEqual(len(json.loads(self.output.read_text())["entries"]), 3)

    def test_rejects_stale_progress_before_provider_call(self):
        self.progress.write_text(json.dumps({"item_id": "a", "stem_hash": "0" * 64,
                                             "embedding": [1, 0]}) + "\n")
        calls = []
        with self.assertRaises(ValueError):
            backfill(self.source, self.progress, self.output,
                     embed=lambda stem: calls.append(stem) or [1, 0])
        self.assertEqual(calls, [])

    def test_checkpoint_binds_inventory_and_model_before_provider_calls(self):
        backfill(self.source, self.progress, self.output,
                 embed=lambda stem: [1, 0], max_new=1)
        lines = self.progress.read_text().splitlines()
        header = json.loads(lines[0])
        self.assertEqual(header["embedding_model"], "gemini-embedding-001")
        self.assertEqual(header["inventory_digest"],
                         json.loads(self.source.read_text())["inventory_digest"])
        for field, value in (("embedding_model", "other-model"),
                             ("inventory_digest", "0" * 64)):
            with self.subTest(field=field):
                bad = {**header, field: value}
                self.progress.write_text(json.dumps(bad) + "\n" + "\n".join(lines[1:]) + "\n")
                calls = []
                with self.assertRaises(ValueError):
                    backfill(self.source, self.progress, self.output,
                             embed=lambda stem: calls.append(stem) or [1, 0])
                self.assertEqual(calls, [])
        self.progress.write_text("\n".join(lines) + "\n")

    def test_invalid_source_hash_rejected(self):
        obj = json.loads(self.source.read_text())
        obj["stems"][0]["stem"] = "Modified"
        self.source.write_text(json.dumps(obj))
        with self.assertRaisesRegex(ValueError, "hashes"):
            load_source(self.source)

    def test_provider_failure_keeps_completed_checkpoint(self):
        def embed(stem):
            if stem.endswith("b"):
                raise RuntimeError("provider down")
            return [1, 0]
        with self.assertRaises(RuntimeError):
            backfill(self.source, self.progress, self.output, embed=embed)
        self.assertEqual(len(load_progress(self.progress, self.entries)), 1)
        self.assertFalse(self.output.exists())

    def test_bad_vector_and_dimension_fail(self):
        for vector in ([0, 0], [1e308, 0], [1], [1, 0, 0]):
            calls = 0
            def embed(stem):
                nonlocal calls
                calls += 1
                return [1, 0] if calls == 1 else vector
            if self.progress.exists():
                self.progress.unlink()
            with self.subTest(vector=vector), self.assertRaises(ValueError):
                backfill(self.source, self.progress, self.output, embed=embed)
            self.assertEqual(len(load_progress(self.progress, self.entries)), 1)


if __name__ == "__main__":
    unittest.main()
