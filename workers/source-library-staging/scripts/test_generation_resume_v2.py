"""Offline checkpoint contract tests: no API calls or database writes."""
import unittest
from unittest.mock import patch
from item_generation_runner_v2 import generate_one

EVIDENCE = [{"passage_id": "p1", "textbook_id": "t1", "excerpt": "Example evidence."}]
CONCEPT = {"objective": "I.A.1", "mechanism": "Mechanism", "relevance": "Relevance",
           "misconception": "Misconception", "counterfactual": "Counterfactual",
           "evidence_ids": ["p1"]}
DRAFT = {"format": "MC", "stem": "Which option is correct?"}
KW = dict(mode="NCE", domain="I", section="A", objective="I.A.1",
          evidence=EVIDENCE, format="MC", item_id="test-1")

class ResumeTests(unittest.TestCase):
    def test_resume_at_rationale_skips_two_paid_calls(self):
        calls = []
        def adapter(req):
            calls.append(req["step"])
            return {"core_concept": "c", "why_key_wins": "w",
                    "trap": "t", "distractor_breakdown": {"B": "incorrect"}}
        with patch("item_generation_runner_v2.validate_complete_item", return_value=[]), \
             patch("item_generation_runner_v2.reconcile", return_value=[]), \
             patch("item_generation_runner_v2.answer_evidence_check", return_value=[]):
            generate_one(adapter, **KW, checkpoint={"concept_card": CONCEPT, "draft": DRAFT})
        self.assertEqual(calls, ["rationale"])

    def test_checkpoint_emitted_before_next_stage(self):
        saved = []
        def adapter(req):
            if req["step"] == "concept_card": return dict(CONCEPT)
            if req["step"] == "item_draft": return dict(DRAFT)
            raise RuntimeError("rate limited")
        with self.assertRaisesRegex(RuntimeError, "rate limited"):
            generate_one(adapter, **KW, on_checkpoint=lambda stage, value: saved.append(stage))
        self.assertEqual(saved, ["concept_card", "draft"])

    def test_resume_rejects_mismatched_evidence(self):
        bad = dict(CONCEPT, evidence_ids=["unknown"])
        with self.assertRaisesRegex(ValueError, "unknown passages"):
            generate_one(lambda _: self.fail("model should not be called"), **KW,
                         checkpoint={"concept_card": bad, "draft": DRAFT})

if __name__ == "__main__":
    unittest.main()
