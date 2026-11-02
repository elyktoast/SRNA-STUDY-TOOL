"""Human visual review metadata tests; no private textbook pages used."""
import json
import tempfile
import unittest
from pathlib import Path

from review_image_assets import create_review, validate_review


class ImageReviewTests(unittest.TestCase):
    def test_pending_by_default_and_source_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({"sha256": "a" * 64}))
            (root / "image_assets.json").write_text(json.dumps([
                {"asset_id": "p0001-x7-n1"}, {"asset_id": "p0002-x8-n1"}
            ]))
            review = create_review(root)
            self.assertEqual([d["decision"] for d in review["decisions"]], ["pending", "pending"])
            self.assertEqual(validate_review(root, review)["pending"], 2)
            review["decisions"][0]["decision"] = "relevant"
            self.assertEqual(validate_review(root, review)["relevant"], 1)
            review["decisions"][1]["asset_id"] = "unknown"
            with self.assertRaisesRegex(ValueError, "references"):
                validate_review(root, review)
            review["decisions"][1]["asset_id"] = "p0002-x8-n1"
            (root / "manifest.json").write_text(json.dumps({"sha256": "b" * 64}))
            with self.assertRaisesRegex(ValueError, "Stale"):
                validate_review(root, review)

    def test_rejects_duplicate_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({"sha256": "a" * 64}))
            (root / "image_assets.json").write_text(json.dumps([
                {"asset_id": "duplicate"}, {"asset_id": "duplicate"}
            ]))
            with self.assertRaisesRegex(ValueError, "duplicate"):
                create_review(root)
