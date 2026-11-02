import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nbcrna_item_formats import validate

class FormatTests(unittest.TestCase):
    def test_multi_eight_choices(self):
        item = {"type": "multi", "options": list("ABCDEFGH"), "answer": [1, 4, 7], "selectCount": 3}
        self.assertEqual(validate(item), [])
        item["selectCount"] = 2
        self.assertIn("Selection count must equal keyed answers", validate(item))

    def test_numeric_entry(self):
        self.assertEqual(validate({"type": "calculation", "numericAnswer": 2.5, "decimalPlaces": 1, "units": "mg"}), [])
        self.assertTrue(validate({"type": "calculation", "numericAnswer": "two", "decimalPlaces": 1, "units": "mg"}))

    def test_matching_modes(self):
        item = {"type": "drag_drop", "dragMode": "match_multiple_use",
                "tokens": ["A", "B"], "targets": ["1", "2", "3"], "mapping": [0, 1, 0]}
        self.assertEqual(validate(item), [])
        item["dragMode"] = "match_single_use"
        self.assertTrue(validate(item))

    def test_hotspot(self):
        item = {"type": "hotspot", "imageAssetId": "asset1",
                "correctRegion": {"shape": "rect", "x": 0.2, "y": 0.2, "width": 0.4, "height": 0.4}}
        self.assertEqual(validate(item), [])
        item["correctRegion"]["width"] = 0.9
        self.assertTrue(validate(item))

if __name__ == "__main__":
    unittest.main()
