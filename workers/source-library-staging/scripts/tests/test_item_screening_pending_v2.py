import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_screening_orchestrator import screen
from test_item_standard_v2 import sample

class PendingChecksTests(unittest.TestCase):
    def test_missing_embeddings_are_pending(self):
        result = screen(sample())
        self.assertEqual(result["stages"]["duplicates"]["status"], "pending")
        self.assertEqual(result["stages"]["blind_model"]["status"], "pending")
        self.assertFalse(result["screening_complete"])
        self.assertFalse(result["can_publish"])
    def test_semantic_match_is_flagged(self):
        item = sample()
        result = screen(item, embedding=[1.0, 0.0],
                        neighbors=[{"item_id": "other", "embedding": [1.0, 0.0]}])
        self.assertIn(result["stages"]["duplicates"]["status"], ("flag", "fail"))

if __name__ == "__main__":
    unittest.main()
