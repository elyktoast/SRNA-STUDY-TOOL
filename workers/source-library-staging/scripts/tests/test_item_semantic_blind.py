import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_semantic_duplicates import cosine, screen
from item_blind_review_scoring import compare

class ScreeningTests(unittest.TestCase):
    def test_cosine_and_threshold(self):
        self.assertAlmostEqual(cosine([1, 0], [1, 0]), 1)
        self.assertEqual(screen([1, 0], [{"item_id": "q2", "embedding": [1, 0]},
                                          {"item_id": "q3", "embedding": [0, 1]}]),
                         [{"item_id": "q2", "similarity": 1.0}])
        with self.assertRaises(ValueError):
            cosine([0, 0], [1, 0])
    def test_numeric_blind(self):
        item = {"item_id": "q", "format": "SA", "sa": {"answer": 5, "tolerance": 0}}
        self.assertEqual(compare(item, {"item_id": "q", "numeric_answer": 5}), [])
        self.assertTrue(compare(item, {"item_id": "q", "numeric_answer": 6}))
    def test_dd_blind(self):
        item = {"item_id": "q", "format": "DD", "dd": {"pairs": {"a": "x"}}}
        self.assertEqual(compare(item, {"item_id": "q", "pairs": {"a": "x"}}), [])
        self.assertTrue(compare(item, {"item_id": "q", "pairs": {"a": "y"}}))
    def test_hotspot_blind(self):
        item = {"item_id": "q", "format": "HS", "hs": {"correct_region": "r1"}}
        self.assertEqual(compare(item, {"item_id": "q", "region": "r1"}), [])
        self.assertTrue(compare(item, {"item_id": "q", "region": "r2"}))

if __name__ == "__main__":
    unittest.main()
