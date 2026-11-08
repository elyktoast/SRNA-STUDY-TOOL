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
    def test_invalid_neighbors_fail_closed(self):
        for neighbors in ([{"item_id": "same", "embedding": [1, 0]},
                           {"item_id": "same", "embedding": [0, 1]}],
                          [{"item_id": "", "embedding": [1, 0]}],
                          [{"item_id": "x", "embedding": [1]}],
                          [{"item_id": "x", "embedding": [float("nan"), 0]}],
                          [None]):
            with self.subTest(neighbors=repr(neighbors)):
                with self.assertRaises(ValueError):
                    screen([1, 0], neighbors)

    def test_malformed_blind_choice_flags_without_exception(self):
        item = {"item_id": "q", "format": "MC", "key": ["A"]}
        for response in ({"item_id": "q", "key": [["A"]]},
                         {"item_id": "q", "key": [None]},
                         {"item_id": "q", "key": ["A", "A"]},
                         {"item_id": "q", "key": "A"}):
            with self.subTest(response=response):
                issues = compare(item, response)
                self.assertTrue(issues)
                self.assertEqual(issues[0]["rule_id"], "R-12.1")

    def test_empty_neighbor_validation(self):
        self.assertEqual(screen([1.0, 0.0], []), [])
        for vector in ([], [0.0, 0.0], [float("nan"), 0.0], ["bad", 1.0], None):
            with self.subTest(vector=vector):
                with self.assertRaises(ValueError):
                    screen(vector, [])
        for threshold in (float("nan"), float("inf"), -1):
            with self.assertRaises(ValueError):
                screen([1.0, 0.0], [], threshold=threshold)

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
