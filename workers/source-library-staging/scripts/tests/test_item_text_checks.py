import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_text_checks import check

class EditorialTests(unittest.TestCase):
    def test_short_multiword_drug_name_is_not_a_length_cue_when_visibly_shorter(self):
        item={"format":"MC","key":["C"],"options":[{"id":"A","text":"Desflurane"},
              {"id":"B","text":"Succinylcholine"},{"id":"C","text":"Nitrous oxide"},
              {"id":"D","text":"Isoflurane"}]}
        self.assertNotIn("R-6.8",{i["rule_id"] for i in check(item)})

    def test_actually_longer_short_key_still_flags(self):
        item={"format":"MC","key":["A"],"options":[{"id":"A","text":"Substantially longer explanation"},
              {"id":"B","text":"Small option"},{"id":"C","text":"Other choice"}]}
        self.assertIn("R-6.8",{i["rule_id"] for i in check(item)})

    def test_length(self):
        item = {"format": "MC", "key": ["A"], "stem": "Question?",
                "options": [{"id": k, "text": t} for k,t in zip("ABCD",
                ["A substantially longer explanation than others", "Other", "Third", "Fourth"])]}
        self.assertIn("R-6.8", {e["rule_id"] for e in check(item)})
    def test_verbatim_overlap(self):
        item = {"format": "MC", "key": ["A"],
                "stem": "One two three four five six seven eight nine?",
                "options": [{"id": k, "text": t} for k,t in zip("ABCD", ["Alpha", "Beta", "Gamma", "Delta"])]}
        self.assertIn("R-2.8", {e["rule_id"] for e in check(item,
                      ["one two three four five six seven eight nine ten"])})
    def test_no_overlap(self):
        item = {"format": "MC", "key": ["A"], "stem": "Which value?",
                "options": [{"id": k, "text": t} for k,t in zip("ABCD", ["One", "Two", "Three", "Four"])]}
        self.assertEqual(check(item), [])

if __name__ == "__main__":
    unittest.main()
