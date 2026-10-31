"""Reviewed image candidate export tests."""
import json
import tempfile
import unittest
from pathlib import Path

from export_reviewed_image_candidates import approved_candidates
from review_image_assets import create_review


class CandidateExportTests(unittest.TestCase):
    def test_only_explicitly_relevant_images_are_exported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "manifest.json").write_text(json.dumps({"sha256": "a" * 64}))
            (root / "image_assets.json").write_text(json.dumps([
                {"asset_id": "p0001-x3-n1", "pdf_page": 1, "bbox": [0, 0, 10, 10]},
                {"asset_id": "p0001-x4-n1", "pdf_page": 1, "bbox": [20, 20, 30, 30]},
            ]))
            (root / "passage_image_links.json").write_text(json.dumps([
                {"chunk_index": 0, "pdf_page": 1,
                 "candidate_asset_ids": ["p0001-x3-n1", "p0001-x4-n1"]},
            ]))
            review = create_review(root)
            review_path = root / "review.json"
            review_path.write_text(json.dumps(review))
            self.assertEqual(approved_candidates(root, review_path)["passages"], [])
            review["decisions"][0]["decision"] = "relevant"
            review["decisions"][1]["decision"] = "decorative"
            review_path.write_text(json.dumps(review))
            result = approved_candidates(root, review_path)
            self.assertEqual(len(result["passages"]), 1)
            self.assertEqual([a["asset_id"] for a in result["passages"][0]["candidate_assets"]],
                             ["p0001-x3-n1"])
            self.assertFalse(result["passages"][0]["semantic_match_verified"])
            review["source_sha256"] = "b" * 64
            review_path.write_text(json.dumps(review))
            with self.assertRaisesRegex(ValueError, "Stale"):
                approved_candidates(root, review_path)
