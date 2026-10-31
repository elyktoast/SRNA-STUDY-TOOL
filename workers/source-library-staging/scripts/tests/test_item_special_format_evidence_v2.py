import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_special_format_evidence_v2 import check

SOURCES = [{"passage_id": "p1", "excerpt": "Trusted text"}]
def mapped(*keys):
    return {k: {"passage_ids": ["p1"], "explanation": "Source-linked rationale"}
            for k in keys}

class SpecialFormatEvidenceTests(unittest.TestCase):
    def test_numeric_solution_evidence(self):
        self.assertEqual(check({"format": "SA", "distractor_evidence": mapped("solution")}, SOURCES), [])
    def test_matching_four_pairs(self):
        item = {"format": "DD", "dd": {"pairs": {"A": "1", "B": "2", "C": "3", "D": "4"}},
                "distractor_evidence": mapped("pair:A", "pair:B", "pair:C", "pair:D")}
        self.assertEqual(check(item, SOURCES), [])
        del item["distractor_evidence"]["pair:D"]
        self.assertTrue(check(item, SOURCES))
    def test_hotspot_regions(self):
        item = {"format": "HS", "hs": {"correct_region": "r1", "near_miss_regions": ["r2", "r3"]},
                "distractor_evidence": mapped("correct_region", "near_miss:0", "near_miss:1")}
        self.assertEqual(check(item, SOURCES), [])
        item["distractor_evidence"]["near_miss:1"]["passage_ids"] = ["invented"]
        self.assertTrue(check(item, SOURCES))
    def test_missing_numeric_evidence(self):
        self.assertTrue(check({"format": "SA", "distractor_evidence": {}}, SOURCES))

if __name__ == "__main__":
    unittest.main()
