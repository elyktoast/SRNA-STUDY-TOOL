"""Decision persistence tests for the loopback-only image review editor."""
import json
from concurrent.futures import ThreadPoolExecutor
import tempfile
import unittest
from pathlib import Path

from review_image_assets import create_review, validate_review
from serve_image_review import save_decision


class ReviewEditorTests(unittest.TestCase):
    def test_saves_explicit_decision_and_rejects_unknown_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({"sha256": "a" * 64}))
            (root / "image_assets.json").write_text(json.dumps([
                {"asset_id": "p0001-x7-n1"}, {"asset_id": "p0002-x8-n1"}
            ]))
            review_path = root / "review.json"
            review_path.write_text(json.dumps(create_review(root)))
            save_decision(root, review_path, "p0001-x7-n1", "relevant")
            review = json.loads(review_path.read_text())
            self.assertEqual(review["decisions"][0]["decision"], "relevant")
            self.assertEqual(review["decisions"][1]["decision"], "pending")
            self.assertEqual(validate_review(root, review)["reviewed"], 1)
            with self.assertRaisesRegex(ValueError, "Unknown"):
                save_decision(root, review_path, "missing", "decorative")
            with self.assertRaisesRegex(ValueError, "Invalid decision"):
                save_decision(root, review_path, "p0001-x7-n1", "approved")
            self.assertEqual(json.loads(review_path.read_text())["decisions"][0]["decision"], "relevant")

    def test_concurrent_decisions_do_not_erase_each_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({"sha256": "a" * 64}))
            (root / "image_assets.json").write_text(json.dumps([
                {"asset_id": "p0001-x7-n1"}, {"asset_id": "p0002-x8-n1"}
            ]))
            review_path = root / "review.json"
            review_path.write_text(json.dumps(create_review(root)))
            with ThreadPoolExecutor(max_workers=2) as executor:
                jobs = [
                    executor.submit(save_decision, root, review_path, "p0001-x7-n1", "relevant"),
                    executor.submit(save_decision, root, review_path, "p0002-x8-n1", "decorative"),
                ]
                for job in jobs:
                    job.result()
            decisions = {d["asset_id"]: d["decision"] for d in json.loads(review_path.read_text())["decisions"]}
            self.assertEqual(decisions, {"p0001-x7-n1": "relevant", "p0002-x8-n1": "decorative"})

    def test_stale_source_blocks_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({"sha256": "a" * 64}))
            (root / "image_assets.json").write_text(json.dumps([{"asset_id": "p0001-x7-n1"}]))
            review_path = root / "review.json"
            review_path.write_text(json.dumps(create_review(root)))
            (root / "manifest.json").write_text(json.dumps({"sha256": "b" * 64}))
            with self.assertRaisesRegex(ValueError, "Stale"):
                save_decision(root, review_path, "p0001-x7-n1", "relevant")
