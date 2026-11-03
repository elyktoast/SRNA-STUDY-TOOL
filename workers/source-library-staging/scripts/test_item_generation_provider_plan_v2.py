"""Offline tests for explicit, non-executing Phase C provider routing."""
import unittest
from item_generation_provider_plan_v2 import DEFAULT_PLAN, PROJECT_QUOTA_HINTS, choose_provider, validate_plan


class ProviderPlanTests(unittest.TestCase):
    def test_defaults_use_lite_for_concept_and_groq_for_draft_and_rationale(self):
        self.assertEqual(choose_provider(DEFAULT_PLAN, "concept_card")["model"], "gemini-3.5-flash-lite")
        self.assertEqual(choose_provider(DEFAULT_PLAN, "item_draft")["provider"], "groq")
        self.assertEqual(choose_provider(DEFAULT_PLAN, "rationale")["provider"], "groq")

    def test_fallback_requires_explicit_allowlisted_entry(self):
        plan = dict(DEFAULT_PLAN)
        plan["rationale"] = (("groq", "openai/gpt-oss-120b"), ("gemini", "gemini-3.8-flash"))
        result = choose_provider(plan, "rationale", unavailable={("groq", "openai/gpt-oss-120b")})
        self.assertEqual(result["model"], "gemini-3.8-flash")

    def test_all_unavailable_stops_without_paid_request(self):
        self.assertIsNone(choose_provider(DEFAULT_PLAN, "concept_card",
                        unavailable={("gemini", "gemini-3.5-flash-lite")}))

    def test_rejects_unknown_models_and_duplicate_candidates(self):
        plan = dict(DEFAULT_PLAN)
        plan["concept_card"] = (("gemini", "gemini-unverified"),)
        with self.assertRaises(ValueError): validate_plan(plan)
        plan["concept_card"] = (("gemini", "gemini-3.5-flash-lite"),) * 2
        with self.assertRaises(ValueError): validate_plan(plan)

    def test_quota_hints_not_remaining_usage(self):
        self.assertEqual(PROJECT_QUOTA_HINTS[("gemini", "gemini-3.5-flash-lite")]["rpd"], 500)


if __name__ == "__main__":
    unittest.main()
