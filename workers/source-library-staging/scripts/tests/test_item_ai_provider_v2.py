import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_ai_provider_v2 import make_adapter, ProviderError

REQUEST = {"step": "concept_card", "rules_version": "2.0",
           "auto_publish": False, "evidence": [{"excerpt": "Private source"}]}

class ProviderTests(unittest.TestCase):
    def config(self, **overrides):
        def synthetic_transport(**kw):
            request = json.loads(kw["body"]["messages"][1]["content"])
            response = ({"key": ["A"]} if request.get("format") in ("MC", "MS") else
                        {"region": "top"} if request.get("format") == "HS" else
                        {"objective": "III.H.4"}) if request.get("step") == "blind_review" else {"objective": "III.H.4"}
            return {"choices": [{"message": {"content": json.dumps(response)}}]}
        params = dict(endpoint="https://provider.example/v1/chat/completions",
                      api_key="test-secret", model="test-model",
                      transport=synthetic_transport,
                      owner_opt_in=True, staging=True)
        params.update(overrides)
        return params
    def test_opt_in_required(self):
        with self.assertRaises(ValueError):
            make_adapter(**self.config(owner_opt_in=False))
    def test_https_required(self):
        with self.assertRaises(ValueError):
            make_adapter(**self.config(endpoint="http://provider.example"))
    def test_rejects_provider_query_and_nonstandard_port(self):
        for endpoint in ("https://provider.example/v1/chat?token=secret",
                         "https://provider.example:8443/v1/chat"):
            with self.subTest(endpoint=endpoint):
                with self.assertRaisesRegex(ValueError, "Invalid provider endpoint"):
                    make_adapter(**self.config(endpoint=endpoint))

    def test_rejects_oversized_content_before_parsing(self):
        adapter = make_adapter(**self.config(transport=lambda **kw: {
            "choices": [{"message": {"content": "x" * 262145}}]}))
        with self.assertRaises(ProviderError):
            adapter(REQUEST)

    def test_sends_contract_and_parses_json(self):
        seen = []
        def transport(**kwargs):
            seen.append(kwargs)
            return {"choices": [{"message": {"content": '{"objective":"III.H.4"}'}}]}
        result = make_adapter(**self.config(transport=transport))(REQUEST)
        self.assertEqual(result["objective"], "III.H.4")
        self.assertIn("Private source", seen[0]["body"]["messages"][1]["content"])
        self.assertEqual(seen[0]["headers"]["Authorization"], "Bearer test-secret")
    def test_rewrite_requires_single_attempt_and_draft(self):
        adapter = make_adapter(**self.config())
        base = {"step": "rewrite", "rules_version": "2.0",
                "auto_publish": False, "max_rewrites": 1,
                "requires_human_review": True,
                "item": {"status": "draft"}, "issues": [{"rule_id": "R-15"}]}
        self.assertIsInstance(adapter(base), dict)
        for change in ({"max_rewrites": 2}, {"requires_human_review": False},
                       {"issues": "not a list"}, {"item": None}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    adapter({**base, **change})

    def test_blind_review_never_accepts_answer_or_evidence(self):
        adapter = make_adapter(**self.config())
        base = {"step": "blind_review", "rules_version": "2.0",
                "auto_publish": False, "blind": True,
                "item_id": "q1", "stem": "What is the best choice?",
                "format": "MC", "options": [{"id": "A", "text": "One"}]}
        self.assertIsInstance(adapter(base), dict)
        for secret in ("key", "rationale", "evidence", "concept_card",
                       "distractor_evidence", "model", "source_excerpt", "answer"):
            with self.subTest(secret=secret):
                with self.assertRaises(ValueError):
                    adapter({**base, secret: "must not leak"})

    def test_blind_nested_answer_metadata_rejected(self):
        adapter = make_adapter(**self.config())
        base = {"step": "blind_review", "rules_version": "2.0",
                "auto_publish": False, "blind": True, "item_id": "q1",
                "stem": "Select the best answer", "format": "MC",
                "options": [{"id": "A", "text": "One"}]}
        for extra in ({"key": ["A"]}, {"is_correct": True},
                      {"rationale": "secret"}, {"error_pattern": "secret"}):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError):
                    adapter({**base, "options": [{**base["options"][0], **extra}]})
        adapter({**base, "options": [{"id": "A", "text": "One"}]})

    def test_hotspot_blind_figure_metadata_is_restricted(self):
        adapter = make_adapter(**self.config())
        base = {"step": "blind_review", "rules_version": "2.0",
                "auto_publish": False, "blind": True, "item_id": "q1",
                "stem": "Choose the correct region", "format": "HS"}
        adapter({**base, "figure": {"url": "https://example.test/figure.png",
                                     "alt": "Anatomical diagram"}})
        for figure in ({"correct_region": "A"}, {"url": "https://example.test",
                                                   "answer": "A"}, {}, None):
            with self.subTest(figure=figure):
                with self.assertRaises(ValueError):
                    adapter({**base, "figure": figure})

    def test_rejects_non_json_response(self):
        adapter = make_adapter(**self.config(transport=lambda **kw: {
            "choices": [{"message": {"content": "not json"}}]}))
        with self.assertRaises(ProviderError):
            adapter(REQUEST)

    def test_exact_rewrite_item_envelope_unwraps_without_synthesizing_metadata(self):
        item = {"item_id": "q1", "status": "draft", "key": ["B"]}
        adapter = make_adapter(**self.config(transport=lambda **kw: {
            "choices": [{"message": {"content": json.dumps({"item": item})}}]}))
        request = {"step": "rewrite", "rules_version": "2.0", "auto_publish": False,
                   "max_rewrites": 1, "requires_human_review": True,
                   "item": item, "issues": [{"rule_id": "R-2.4"}]}
        self.assertEqual(adapter(request), item)

    def test_rewrite_envelope_with_extra_claims_is_not_unwrapped(self):
        envelope = {"item": {"item_id": "q1"}, "approved": True}
        adapter = make_adapter(**self.config(transport=lambda **kw: {
            "choices": [{"message": {"content": json.dumps(envelope)}}]}))
        request = {"step": "rewrite", "rules_version": "2.0", "auto_publish": False,
                   "max_rewrites": 1, "requires_human_review": True,
                   "item": {"item_id": "q1"}, "issues": [{"rule_id": "R-2.4"}]}
        self.assertEqual(adapter(request), envelope)

    def test_rewrite_protocol_envelope_requires_exact_safe_values(self):
        item = {"item_id": "q1", "status": "draft", "key": ["B"]}
        request = {"step": "rewrite", "rules_version": "2.0", "auto_publish": False,
                   "max_rewrites": 1, "requires_human_review": True,
                   "item": item, "issues": [{"rule_id": "R-6.8"}]}
        for extra,unwrap in [({"rules_version":"2.0","auto_publish":False},True),
                             ({"rules_version":"wrong"},False),({"can_publish":True},False),
                             ({"max_rewrites":2},False),({"auto_publish":0},False)]:
            envelope={"item":item,**extra}
            adapter=make_adapter(**self.config(transport=lambda **kw: {
                "choices":[{"message":{"content":json.dumps(envelope)}}]}))
            self.assertEqual(adapter(request),item if unwrap else envelope)

if __name__ == "__main__":
    unittest.main()
