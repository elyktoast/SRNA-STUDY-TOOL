"""Unit tests for the owner-scoped R2 backlog indexer."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("process_r2_backlog", ROOT / "process_r2_backlog.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

OWNER = "895ed357-27c3-4d4b-a98a-77b0de20760c"


class Paginator:
    def paginate(self, **kwargs):
        yield {"Contents": [
            {"Key": OWNER + "/one.pdf"},
            {"Key": "other/two.pdf"},
            {"Key": OWNER + "/notes.txt"},
            {"Key": OWNER + "/bad name.pdf"},
            {"Key": OWNER + "/two.pdf"},
        ]}


class Client:
    def get_paginator(self, name):
        assert name == "list_objects_v2"
        return Paginator()


class BacklogTests(unittest.TestCase):
    def test_owner_filter_and_limit(self):
        self.assertEqual(module.enumerate_keys(Client(), OWNER, 1), [OWNER + "/one.pdf"])
        self.assertEqual(len(module.enumerate_keys(Client(), OWNER)), 2)

    def test_invalid_pdf_key_does_not_consume_batch_limit(self):
        keys = module.enumerate_keys(Client(), OWNER, limit=2)
        self.assertEqual(keys, [OWNER + "/one.pdf", OWNER + "/two.pdf"])
        self.assertNotIn(OWNER + "/bad name.pdf", keys)

    def test_limit_counts_pending_not_ready(self):
        pending = module.enumerate_keys(
            Client(), OWNER, limit=1, exclude_keys={OWNER + "/one.pdf"})
        self.assertEqual(pending, [OWNER + "/two.pdf"])

    def test_all_ready_returns_no_pending(self):
        pending = module.enumerate_keys(
            Client(), OWNER, limit=1,
            exclude_keys={OWNER + "/one.pdf", OWNER + "/two.pdf"})
        self.assertEqual(pending, [])

    def test_invalid_owner_rejected(self):
        with self.assertRaisesRegex(ValueError, "owner UUID"):
            module.enumerate_keys(Client(), "invalid")

    def test_force_reindex_requires_apply(self):
        with patch.object(module, "run") as runner:
            with self.assertRaisesRegex(ValueError, "requires --apply"):
                module.process_backlog(Client(), OWNER, force_reindex=True)
            runner.assert_not_called()

    def test_invalid_limit_rejected_before_processing(self):
        with patch.object(module, "run") as runner:
            with self.assertRaisesRegex(ValueError, "Limit"):
                module.process_backlog(Client(), OWNER, limit=True)
            runner.assert_not_called()

    def test_malformed_r2_object_key_is_ignored(self):
        class MalformedClient:
            def get_paginator(self, name):
                class P:
                    def paginate(self, **kwargs):
                        yield {"Contents": [{"Key": None}, {"Key": 42},
                                            {"Key": OWNER + "/valid.pdf"}]}
                return P()
        self.assertEqual(module.enumerate_keys(MalformedClient(), OWNER),
                         [OWNER + "/valid.pdf"])

    def test_enumeration_rejects_boolean_limit(self):
        with self.assertRaisesRegex(ValueError, "Limit"):
            module.enumerate_keys(Client(), OWNER, True)

    def test_ready_books_are_skipped_without_reindex(self):
        with patch.object(module, "run", return_value={"indexed": True}) as runner:
            result = module.process_backlog(
                Client(), OWNER, apply=True, ready_keys={OWNER + "/one.pdf"})
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(runner.call_count, 1)
        self.assertEqual(runner.call_args.args[1], OWNER + "/two.pdf")

    def test_dry_run_skips_known_ready_books(self):
        with patch.object(module, "run", return_value={"indexed": False}) as runner:
            result = module.process_backlog(
                Client(), OWNER, apply=False, ready_keys={OWNER + "/one.pdf"})
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual(result["succeeded"], 1)
        self.assertEqual(runner.call_args.args[1], OWNER + "/two.pdf")

    def test_force_reindex_processes_ready_books(self):
        with patch.object(module, "run", return_value={"indexed": True}) as runner:
            result = module.process_backlog(
                Client(), OWNER, apply=True, ready_keys={OWNER + "/one.pdf"},
                force_reindex=True)
        self.assertEqual(result["skipped"], 0)
        self.assertEqual(runner.call_count, 2)

    def test_ocr_option_reaches_r2_runner(self):
        with patch.object(module, "run", return_value={"indexed": False}) as runner:
            module.process_backlog(Client(), OWNER, ocr=True)
        self.assertEqual(runner.call_args.kwargs["ocr"], True)

    def test_summary_excludes_private_runner_fields(self):
        with patch.object(module, "run", return_value={
            "pdf_pages": 12, "passages": 38, "indexed": False,
            "ocr_pages": [3], "ocr_failed_pages": [8],
            "database_url": "postgres://private-credential",
            "passage_text": "private textbook passage",
        }):
            summary = module.process_backlog(Client(), OWNER, limit=1)
        self.assertEqual(summary["results"][0]["result"]["pdf_pages"], 12)
        self.assertEqual(summary["results"][0]["result"]["ocr_pages_count"], 1)
        self.assertEqual(summary["results"][0]["result"]["ocr_failed_pages_count"], 1)
        self.assertNotIn("private-credential", str(summary))
        self.assertNotIn("private textbook passage", str(summary))

    def test_default_dry_run_and_error_isolation(self):
        def fake_run(owner, key, apply, client, ocr=False):
            if key.endswith("two.pdf"):
                raise RuntimeError("private error details")
            return {"indexed": False}
        with patch.object(module, "run", side_effect=fake_run) as runner:
            result = module.process_backlog(Client(), OWNER)
        self.assertEqual(result["mode"], "dry-run")
        self.assertEqual((result["succeeded"], result["failed"]), (1, 1))
        self.assertEqual(runner.call_args_list[0].kwargs["apply"], False)
        self.assertEqual(result["results"][1]["error_type"], "RuntimeError")
        self.assertNotIn("private error details", str(result))


if __name__ == "__main__":
    unittest.main()
