import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_duplicate_checks import detect, stem_fingerprint

class DuplicateChecksTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(stem_fingerprint("Which  drug?"), stem_fingerprint("WHICH drug?!"))
    def test_duplicate_detected(self):
        issues = detect({"stem": "Which drug?"}, ["Which drug?!"])
        self.assertEqual(issues[0]["rule_id"], "R-11")
    def test_distinct_stems(self):
        self.assertEqual(detect({"stem": "Which drug?"}, ["Which airway?"]), [])
    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            stem_fingerprint(" ")

if __name__ == "__main__":
    unittest.main()
