import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backfill_semantic_embeddings_v2 import backfill
from finalize_semantic_checkpoint_v2 import finalize


class FinalizeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source = root / "source.json"
        self.progress = root / "progress.jsonl"
        self.output = root / "bundle.json"
        stem = "Canonical question"
        entries = [{"item_id": "a", "stem_hash": hashlib.sha256(stem.encode()).hexdigest()}]
        digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
        self.source.write_text(json.dumps({"schema_version": 1, "inventory_digest": digest,
                                            "item_count": 1, "entries": entries,
                                            "stems": [{"item_id": "a", "stem": stem}]}))
        self.env = {"STAGING_ONLY": "true"}

    def test_missing_checkpoint_does_not_upload(self):
        calls = []
        result = finalize(self.source, self.progress, self.output, "run-1",
                          env=self.env, transport=lambda *a, **k: calls.append(a))
        self.assertEqual(result["reason"], "no_checkpoint")
        self.assertEqual(calls, [])

    def test_valid_partial_checkpoint_uploads(self):
        backfill(self.source, self.progress, self.output,
                 embed=lambda _: [1.0, 0.0], max_new=1)
        calls = []
        def save(mode, path, **kwargs):
            calls.append((mode, kwargs["snapshot"]))
            return {"saved": True}
        result = finalize(self.source, self.progress, self.output, "run-2",
                          env=self.env, transport=save)
        self.assertEqual(result["indexed"], 1)
        self.assertEqual(calls, [("save", "run-2")])

    def test_corrupt_checkpoint_fails_before_upload(self):
        self.progress.write_text('{"broken":true}\n')
        calls = []
        with self.assertRaises(ValueError):
            finalize(self.source, self.progress, self.output, "run-3",
                     env=self.env, transport=lambda *a, **k: calls.append(a))
        self.assertEqual(calls, [])

    def test_staging_required(self):
        with self.assertRaises(ValueError):
            finalize(self.source, self.progress, self.output, "run-4",
                     env={}, transport=lambda *a, **k: {"saved": True})


if __name__ == "__main__":
    unittest.main()
