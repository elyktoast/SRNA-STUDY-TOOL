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
    def test_trusted_model_overrides_untrusted_model_before_validation(self):
        def adapter(request):
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                draft = sample()
                draft["model"] = "forged-model"
                return draft
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        result = generate_one(adapter, **ARGS, generator_model_id="trusted-model")
        self.assertEqual(result["item"]["model"], "trusted-model")
        self.assertFalse(result["auto_approved"])

    def test_unknown_evidence_stops_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="o", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids=["unknown"])
        with self.assertRaises(ValueError):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])
    def test_duplicate_concept_citations_stop_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="III.H.4", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids=["p1", "p1"])
        with self.assertRaisesRegex(ValueError, "unique passage IDs"):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])

    def test_invalid_concept_citation_type_stops_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="III.H.4", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids="p1")
        with self.assertRaises(ValueError):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])

    def test_untrusted_draft_cannot_override_review_or_identity(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                draft = sample()
                draft.update(item_id="model-forged-id", mode="SEE", domain="I",
                             section="forged", objective="forged", format="MC",
                             status="approved", rules_version="1.0")
                return draft
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        result = generate_one(adapter, **ARGS)
        item = result["item"]
        for field, expected in (("item_id", "new-1"), ("mode", "NCE"),
                                ("domain", "III"), ("section", "III.H"),
                                ("objective", "III.H.4"), ("status", "draft"),
                                ("rules_version", "2.0")):
            with self.subTest(field=field):
                self.assertEqual(item[field], expected)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        self.assertFalse(result["auto_approved"])
        self.assertFalse(result["database_writes"])

    def test_malformed_adapter_response_stops_pipeline(self):
        for invalid in (None, [], "not-json"):
            with self.subTest(response=repr(invalid)):
                calls = []
                def adapter(request):
                    calls.append(request["step"])
                    return invalid
                with self.assertRaisesRegex(ValueError, "JSON object"):
                    generate_one(adapter, **ARGS)
                self.assertEqual(calls, ["concept_card"])

    def test_no_implicit_model_calls(self):
        with self.assertRaises(ValueError):
            generate_one(None, **ARGS)

if __name__ == "__main__":
    unittest.main()
