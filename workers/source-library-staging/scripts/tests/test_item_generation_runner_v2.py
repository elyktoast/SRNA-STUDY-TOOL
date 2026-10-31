import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_runner_v2 import generate_one
from test_item_standard_v2 import sample

EVIDENCE = [{"passage_id": "p1", "textbook_id": "t1", "excerpt": "Source"}]
ARGS = dict(mode="NCE", domain="III", section="III.H", objective="III.H.4",
            evidence=EVIDENCE, format="MC", item_id="new-1")

class RunnerTests(unittest.TestCase):
    def test_three_separate_calls_and_never_approve(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                return dict(sample())
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        result = generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        self.assertEqual(result["item"]["status"], "draft")
        self.assertFalse(result["auto_approved"])
        self.assertFalse(result["database_writes"])
    def test_unknown_evidence_stops_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="o", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids=["unknown"])
        with self.assertRaises(ValueError):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])
    def test_no_implicit_model_calls(self):
        with self.assertRaises(ValueError):
            generate_one(None, **ARGS)

if __name__ == "__main__":
    unittest.main()
