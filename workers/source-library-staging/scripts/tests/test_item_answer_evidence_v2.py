import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_answer_evidence_v2 import check

SOURCE = [{"passage_id": "p1", "excerpt": "A trusted indexed passage"}]
def item():
    return {"format": "MC", "options": [{"id": x} for x in "ABCD"], "key": ["A"],
            "distractor_evidence": {x: {
                "verdict": "supports_key" if x == "A" else "refutes_distractor",
                "passage_ids": ["p1"], "explanation": "Requires faculty verification"
            } for x in "ABCD"}}

class EvidenceTests(unittest.TestCase):
    def test_all_options_have_traceability(self):
        self.assertEqual(check(item(), SOURCE), [])
    def test_missing_distractor_rejected(self):
        x = item()
        del x["distractor_evidence"]["D"]
        self.assertTrue(check(x, SOURCE))
    def test_unknown_source_rejected(self):
        x = item()
        x["distractor_evidence"]["A"]["passage_ids"] = ["invented"]
        self.assertTrue(check(x, SOURCE))
    def test_wrong_verdict_rejected(self):
        x = item()
        x["distractor_evidence"]["B"]["verdict"] = "supports_key"
        self.assertTrue(check(x, SOURCE))
    def test_other_formats_fail_closed(self):
        self.assertTrue(check({"format": "SA"}, SOURCE))

if __name__ == "__main__":
    unittest.main()
