import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_answer_evidence_v2 import check

SOURCE = [{"passage_id": "p1", "excerpt": "A trusted indexed passage"}]
def item():
    return {"format": "MC", "evidence": [{"passage_id": "p1"}], "options": [{"id": x} for x in "ABCD"], "key": ["A"],
            "distractor_evidence": {x: {
                "verdict": "supports_key" if x == "A" else "refutes_distractor",
                "passage_ids": ["p1"], "explanation": "Requires faculty verification"
            } for x in "ABCD"}}

class EvidenceTests(unittest.TestCase):
    def test_all_options_have_traceability(self):
        self.assertEqual(check(item(), SOURCE), [])
    def test_uncited_option_evidence_rejected(self):
        x = item()
        x["evidence"] = []
        self.assertTrue(any("absent from item citations" in issue["message"] for issue in check(x, SOURCE)))

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
    def test_source_silence_does_not_refute_distractor(self):
        x = item()
        x["distractor_evidence"]["B"]["explanation"] = (
            "The passage does not mention the use of muscle relaxants.")
        issues = check(x, SOURCE)
        self.assertTrue(any(issue["rule_id"] == "R-2.4" for issue in issues))

    def test_other_formats_fail_closed(self):
        self.assertTrue(check({"format": "SA"}, SOURCE))

    def test_not_endorsed_is_source_silence_not_a_contradiction(self):
        x=item()
        x["distractor_evidence"]["B"]["explanation"]="The passage does not endorse the proposed duration."
        self.assertTrue(any(issue["rule_id"]=="R-2.4" for issue in check(x,SOURCE)))

if __name__ == "__main__":
    unittest.main()
