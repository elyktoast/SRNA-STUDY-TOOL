import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_item_standard_v2 import sample
from item_draft_intake import intake

class DraftIntakeTests(unittest.TestCase):
    def test_v2_drafts_remain_unapproved(self):
        item = sample()
        result = intake({"questions": [item]})
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["auto_approved"])
        self.assertFalse(result["database_writes"])
        self.assertFalse(result["draft_reviews"][0]["screening"]["can_publish"])
    def test_legacy_rejected(self):
        with self.assertRaises(ValueError):
            intake({"questions": [{"item_id": "old", "type": "single"}]})
    def test_duplicate_ids_rejected(self):
        item = sample()
        with self.assertRaises(ValueError):
            intake({"questions": [item, dict(item)]})
    def test_duplicate_stems_in_batch(self):
        first = sample()
        second = dict(first, item_id="new-2")
        result = intake({"questions": [first, second]})
        self.assertEqual(result["draft_reviews"][1]["screening"]["stages"]["duplicates"]["status"], "fail")

if __name__ == "__main__":
    unittest.main()
