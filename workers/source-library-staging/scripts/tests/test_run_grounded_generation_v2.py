import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_grounded_generation_v2 import execute

ARGS = SimpleNamespace(owner_uid="owner", topic="airway", textbook_id=None, limit=8,
    section_id=None, include_subsections=False, page_start=None, page_end=None,
    mode="NCE", format="MC", execute=False, confirm_paid_calls=False,
    domain="III", section="H", objective="III.H.4", item_id="draft-1")
EVIDENCE = {"topic": "airway", "evidence_count": 1,
            "can_generate_grounded_questions": True, "sources": [{"passage_id": "p1", "textbook_id": "00000000-0000-4000-8000-000000000002"}]}

class GenerationCliTests(unittest.TestCase):
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_default_preflight_never_calls_provider(self, transport, evidence):
        result = execute(object(), ARGS, {"STAGING_ONLY": "true"})
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["can_publish"])
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_paid_calls_require_two_opt_ins(self, transport, evidence):
        args = SimpleNamespace(**{**vars(ARGS), "execute": True})
        with self.assertRaisesRegex(ValueError, "explicit opt-in"):
            execute(object(), args, {"STAGING_ONLY": "true"})
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.generate_from_index")
    @patch("run_grounded_generation_v2.make_adapter")
    @patch("run_grounded_generation_v2.make_transport")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_opted_in_execution_hands_off_to_screened_pipeline(
            self, evidence, transport, adapter, generate):
        args = SimpleNamespace(**{**vars(ARGS), "execute": True,
                                  "textbook_id": "00000000-0000-4000-8000-000000000002",
                                  "confirm_paid_calls": True})
        env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
               "AI_PROVIDER_ENDPOINT": "https://provider.example/v1/chat/completions",
               "AI_ALLOWED_HOSTS": "provider.example",
               "AI_PROVIDER_API_KEY": "secret", "AI_GENERATOR_MODEL": "test-model"}
        generate.return_value = {
            "item_id": "draft-1", "next_state": "needs_editorial_review",
            "source_evidence": {"evidence_count": 1},
            "item": {"id": "draft-1", "stem": "Synthetic test item"},
            "generator_issues": [], "screening": {"can_publish": False},
        }
        result = execute(object(), args, env)
        self.assertFalse(result["dry_run"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])
        self.assertEqual(result["next_state"], "needs_editorial_review")
        self.assertEqual(result["item"]["stem"], "Synthetic test item")
        self.assertTrue(result["requires_human_review"])
        self.assertEqual(result["save_payload"]["evidence"][0]["passage_id"], "p1")
        self.assertEqual(result["save_payload"]["question"]["stem"], "Synthetic test item")
        transport.assert_called_once_with(allowed_hosts=["provider.example"])
        adapter.assert_called_once_with(
            endpoint=env["AI_PROVIDER_ENDPOINT"], api_key="secret",
            model="test-model", transport=transport.return_value,
            owner_opt_in=True, staging=True)
        generate.assert_called_once()
        self.assertEqual(generate.call_args.kwargs["item_id"], "draft-1")
        self.assertEqual(generate.call_args.kwargs["format"], "MC")

    @patch("run_grounded_generation_v2.generate_from_index")
    @patch("run_grounded_generation_v2.make_transport")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_paid_execution_rejects_nonallowlisted_endpoint(
            self, evidence, transport, generate):
        args = SimpleNamespace(**{**vars(ARGS), "execute": True,
                                  "confirm_paid_calls": True})
        env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
               "AI_PROVIDER_ENDPOINT": "https://untrusted.example/v1",
               "AI_ALLOWED_HOSTS": "provider.example"}
        with self.assertRaisesRegex(ValueError, "allowlist"):
            execute(object(), args, env)
        transport.assert_not_called()
        generate.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence")
    @patch("run_grounded_generation_v2.make_transport")
    def test_invalid_blueprint_rejected_before_retrieval_and_provider(self, transport, evidence):
        for change in ({"section": "III.H"}, {"objective": "II.H.4"},
                       {"domain": "V"}, {"format": "TF"}):
            with self.subTest(change=change):
                args = SimpleNamespace(**{**vars(ARGS), **change, "execute": True,
                                          "confirm_paid_calls": True})
                with self.assertRaisesRegex(ValueError, "blueprint"):
                    execute(object(), args, {"STAGING_ONLY": "true",
                                             "AI_GENERATION_OPT_IN": "true"})
        evidence.assert_not_called()
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence")
    def test_no_staging_no_retrieval(self, evidence):
        with self.assertRaisesRegex(ValueError, "Staging-only"):
            execute(object(), ARGS, {})
        evidence.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence", return_value={
        "topic": "airway", "evidence_count": 0,
        "can_generate_grounded_questions": False, "sources": []})
    def test_no_sources_no_generation(self, evidence):
        with self.assertRaisesRegex(ValueError, "No indexed"):
            execute(object(), ARGS, {"STAGING_ONLY": "true"})

if __name__ == "__main__":
    unittest.main()
