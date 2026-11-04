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
        params = dict(endpoint="https://provider.example/v1/chat/completions",
                      api_key="test-secret", model="test-model",
                      transport=lambda **kw: {"choices": [{"message": {
                          "content": json.dumps({"objective": "III.H.4"})}}]},
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

    def test_rejects_non_json_response(self):
        adapter = make_adapter(**self.config(transport=lambda **kw: {
            "choices": [{"message": {"content": "not json"}}]}))
        with self.assertRaises(ProviderError):
            adapter(REQUEST)

if __name__ == "__main__":
    unittest.main()
