"""No-network staging integration smoke test across provider, generation, screening and blind review."""
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_ai_provider_v2 import make_adapter
from item_generation_screened_v2 import generate_and_screen
from item_independent_blind_v2 import review
from test_item_standard_v2 import sample

SOURCE = [{"passage_id": "p1", "textbook_id": "t1",
           "excerpt": "Source evidence states the correct option is alpha.",
           "pdf_page_start": 1}]
ARGS = dict(mode="NCE", domain="III", section="H",
            objective="III.H.4", evidence=SOURCE, format="MC", item_id="new-1")

class StagingIntegrationTests(unittest.TestCase):
    def test_mocked_three_calls_screening_and_blind_review(self):
        draft = copy.deepcopy(sample())
        draft["evidence"] = [{"passage_id": "p1", "textbook_id": "t1",
                               "pdf_page": 1, "excerpt": "correct option is alpha",
                               "printed_page_verified": False}]
        draft["distractor_evidence"] = {k: {
            "verdict": "supports_key" if k == "A" else "refutes_distractor",
            "passage_ids": ["p1"], "explanation": "Faculty must verify support"
        } for k in "ABCD"}
        concept = dict(objective="III.H.4", mechanism="mechanism",
                       relevance="relevance", misconception="misconception",
                       counterfactual="counterfactual", evidence_ids=["p1"])
        rationale = dict(core_concept="concept", why_key_wins="key",
                         trap="trap", distractor_breakdown={"B": "wrong"})
        outputs = [concept, draft, rationale]
        calls = []
        def transport(**kwargs):
            request = json.loads(kwargs["body"]["messages"][1]["content"])
            calls.append(request["step"])
            return {"choices": [{"message": {"content": json.dumps(outputs[len(calls)-1])}}]}
        adapter = make_adapter(endpoint="https://provider.example/v1/chat/completions",
                               api_key="mock-only", model="generator-test",
                               transport=transport, owner_opt_in=True, staging=True)
        result = generate_and_screen(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        self.assertEqual(result["generator_issues"], [])
        self.assertIsNotNone(result["screening"])
        self.assertEqual(result["screening"]["stages"]["duplicates"]["status"], "pending")
        self.assertEqual(result["screening"]["stages"]["blind_model"]["status"], "pending")
        self.assertFalse(result["can_publish"])
        blind_payloads = []
        def reviewer(payload):
            blind_payloads.append(payload)
            return {"item_id": "new-1", "key": ["A"]}
        blind = review(result["item"], reviewer, generator_model_id="generator-test",
                       reviewer_model_id="independent-test")
        self.assertEqual(blind["status"], "pass")
        self.assertNotIn("key", blind_payloads[0])
        self.assertNotIn("evidence", blind_payloads[0])
        self.assertFalse(blind["can_publish"])

if __name__ == "__main__":
    unittest.main()
