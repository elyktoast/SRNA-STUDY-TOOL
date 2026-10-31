import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_page_review_v2 import load_reviewed_pages

DIGEST = "a" * 64
def manifest():
    return {"sha256": DIGEST, "owner_uid": "owner", "r2_key": "owner/book.pdf", "pdf_page_count": 10}
def record():
    return {"schema_version": 1, "source_sha256": DIGEST, "owner_uid": "owner",
            "r2_key": "owner/book.pdf", "reviews": [
                {"pdf_page": 3, "decision": "text_verified", "reviewer_id": "admin",
                 "reviewed_at": "2026-10-31T12:00:00Z", "note": "Checked original page"}]}
class PageReviewTests(unittest.TestCase):
    def read(self, document, source=None):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "review.json"
            p.write_text(json.dumps(document))
            return load_reviewed_pages(p, source or manifest())
    def test_valid_record(self):
        self.assertEqual(self.read(record()), (3,))
    def test_wrong_source_rejected(self):
        r = record()
        r["source_sha256"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "digest mismatch"): self.read(r)
    def test_duplicate_review_rejected(self):
        r = record()
        r["reviews"].append(dict(r["reviews"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate"): self.read(r)
    def test_missing_reviewer_rejected(self):
        r = record()
        del r["reviews"][0]["reviewer_id"]
        with self.assertRaisesRegex(ValueError, "Reviewer"): self.read(r)
if __name__ == "__main__":
    unittest.main()
