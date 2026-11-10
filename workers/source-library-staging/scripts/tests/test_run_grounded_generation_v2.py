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
    def test_choice_quality_checks_do_not_replace_special_format_validation(self, evidence):
        args = SimpleNamespace(**{**vars(ARGS), "format":"SA"})
        env = {"STAGING_ONLY":"true", "AI_GENERATOR_MODEL":"generator", "AI_REVIEWER_MODEL":"reviewer",
               "AI_BLIND_REVIEW_OPT_IN":"true", "AI_EXPLANATION_REVIEW_OPT_IN":"true"}
        result = execute(object(), args, env)
        self.assertEqual(result["review_readiness"]["board_quality_review"],"disabled")
        self.assertEqual(result["review_readiness"]["blind_review"],"configured")
        self.assertEqual(result["review_readiness"]["explanation_review"],"configured")

    @patch("run_grounded_generation_v2.fingerprint", return_value="a"*64)
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_cloudflare_delivery_is_explicit_and_changes_checkpoint_identity(self, evidence, fingerprint):
        base={"STAGING_ONLY":"true", "AI_GENERATOR_MODEL":"test-model"}
        cf=execute(object(), ARGS, {**base, "AI_AUTHORING_PROVIDER":"cloudflare", "AI_CLOUDFLARE_MODEL":"@cf/test-model"})
        self.assertEqual(cf["authoring_provider"], "cloudflare")
        self.assertEqual(cf["authoring_delivery_model"], "@cf/test-model")
        self.assertEqual(fingerprint.call_args_list[0].args[0]["authoring_provider"], "cloudflare")
        with self.assertRaisesRegex(ValueError, "must match"):
            execute(object(), ARGS, {**base, "AI_AUTHORING_PROVIDER":"cloudflare", "AI_CLOUDFLARE_MODEL":"@cf/other-model"})

    @patch("run_grounded_generation_v2.generate_from_index")
    @patch("run_grounded_generation_v2.make_adapter")
    @patch("run_grounded_generation_v2.make_transport")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_cloudflare_provenance_and_mc_plan_requirement(self, evidence, transport, adapter, generate):
        args=SimpleNamespace(**{**vars(ARGS), "execute":True, "confirm_paid_calls":True,
                               "textbook_id":"00000000-0000-4000-8000-000000000002"})
        env={"STAGING_ONLY":"true", "AI_GENERATION_OPT_IN":"true",
             "AI_PROVIDER_ENDPOINT":"https://provider.example/v1/chat/completions", "AI_ALLOWED_HOSTS":"provider.example",
             "AI_PROVIDER_API_KEY":"secret", "AI_GENERATOR_MODEL":"test-model",
             "AI_AUTHORING_PROVIDER":"cloudflare", "AI_CLOUDFLARE_MODEL":"@cf/test-model",
             "STAGING_RECEIPT_SIGNING_SECRET":"a"*48}
        generate.return_value={"item_id":"draft-1", "next_state":"needs_editorial_review", "source_evidence":{},
            "item":{"item_id":"draft-1","stem":"Synthetic"}, "generator_issues":[], "screening":{"can_publish":False}}
        result=execute(object(), args, env)
        self.assertEqual(result["save_payload"]["provider"], "api.cloudflare.com")
        self.assertEqual(result["save_payload"]["model"], "test-model")
        author=generate.call_args.args[3]
        adapter.return_value.return_value={"objective":"III.H.4"}
        with self.assertRaisesRegex(ValueError, "choice plan incomplete"):
            author({"step":"concept_card","format":"MC"})
        adapter.return_value.return_value={"choice_plan":{}}
        self.assertEqual(author({"step":"concept_card","format":"MC"}), {"choice_plan":{}})

    def test_rate_wait_buffer_never_exceeds_sixty_seconds_or_adds_more_attempts(self):
        from run_grounded_generation_v2 import _call_with_bounded_rate_wait
        from item_ai_https_transport_v2 import TransportError
        from unittest.mock import Mock
        adapter=Mock(side_effect=[TransportError('PROVIDER_RATE_LIMIT',retry_after_seconds=60),{}])
        with patch('time.sleep') as sleep:
            self.assertEqual(_call_with_bounded_rate_wait(adapter,{}),{})
        sleep.assert_called_once_with(60)
        self.assertEqual(adapter.call_count,2)

    @patch("run_grounded_generation_v2.fingerprint")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_explanation_review_changes_checkpoint_identity_and_preflight_never_calls_models(self,evidence,fingerprint):
        fingerprint.return_value="a"*64
        base={"STAGING_ONLY":"true","AI_GENERATOR_MODEL":"generator","AI_REVIEWER_MODEL":"reviewer"}
        disabled=execute(object(),ARGS,base)
        enabled=execute(object(),ARGS,{**base,"AI_EXPLANATION_REVIEW_OPT_IN":"true"})
        self.assertEqual(disabled["review_readiness"]["explanation_review"],"disabled")
        self.assertEqual(enabled["review_readiness"]["explanation_review"],"configured")
        self.assertFalse(fingerprint.call_args_list[0].args[0]["explanation_review_enabled"])
        self.assertTrue(fingerprint.call_args_list[2].args[0]["explanation_review_enabled"])
        self.assertTrue(enabled["dry_run"])
        self.assertFalse(enabled["review_readiness"]["independent_review_completed"])

    @patch("run_grounded_generation_v2.fingerprint")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_checkpoint_hash_changes_with_model_and_review_configuration(self, evidence, fingerprint):
        fingerprint.return_value = "a" * 64
        base = {"STAGING_ONLY": "true", "AI_GENERATOR_MODEL": "generator-a",
                "AI_PROVIDER_ENDPOINT": "https://provider.example/v1"}
        execute(object(), ARGS, base)
        execute(object(), ARGS, {**base, "AI_GENERATOR_MODEL": "generator-b"})
        first = fingerprint.call_args_list[0].args[0]
        second = fingerprint.call_args_list[2].args[0]
        self.assertNotEqual(first["generator_model"], second["generator_model"])
        self.assertIn("reviewer_model", first)
        self.assertIn("rewrite_enabled", first)
        self.assertFalse(first["rewrite_enabled"])

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_default_preflight_never_calls_provider(self, transport, evidence):
        result = execute(object(), ARGS, {"STAGING_ONLY": "true"})
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["can_publish"])
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_preflight_reports_config_only_and_no_draft_write(self, transport, evidence):
        env = {"STAGING_ONLY": "true", "AI_GENERATOR_MODEL": "model-a",
               "AI_PROVIDER_ENDPOINT": "https://provider.example/v1",
               "AI_ALLOWED_HOSTS": "provider.example",
               "AI_PROVIDER_API_KEY": "configured",
               "STAGING_RECEIPT_SIGNING_SECRET": "configured"}
        readiness = execute(object(), ARGS, env)["execution_readiness"]
        self.assertTrue(readiness["indexed_evidence_found"])
        self.assertTrue(readiness["provider_endpoint_allowlisted"])
        self.assertTrue(readiness["generator_model_configured"])
        self.assertTrue(readiness["provider_api_key_configured"])
        self.assertTrue(readiness["relay_secret_configured"])
        self.assertFalse(readiness["provider_connectivity_checked"])
        self.assertEqual(readiness["draft_persistence"], "not_performed_by_cli")
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_preflight_discloses_missing_provider_configuration(self, evidence):
        readiness = execute(object(), ARGS, {"STAGING_ONLY": "true"})["execution_readiness"]
        self.assertFalse(readiness["provider_endpoint_allowlisted"])
        self.assertFalse(readiness["generator_model_configured"])
        self.assertFalse(readiness["provider_api_key_configured"])
        self.assertFalse(readiness["relay_secret_configured"])

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_preflight_allows_review_flags_without_paid_calls(self, transport, evidence):
        env = {"STAGING_ONLY": "true", "AI_BLIND_REVIEW_OPT_IN": "true",
               "AI_REWRITE_OPT_IN": "true"}
        result = execute(object(), ARGS, env)
        self.assertTrue(result["dry_run"])
        self.assertFalse(result["database_writes"])
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_preflight_reports_review_readiness_without_provider_calls(self, transport, evidence):
        env = {"STAGING_ONLY": "true", "AI_GENERATOR_MODEL": "model-a",
               "AI_REVIEWER_MODEL": "model-b", "AI_BLIND_REVIEW_OPT_IN": "true",
               "AI_REWRITE_OPT_IN": "true"}
        readiness = execute(object(), ARGS, env)["review_readiness"]
        self.assertEqual(readiness["blind_review"], "configured")
        self.assertEqual(readiness["rewrite"], "configured")
        self.assertFalse(readiness["independent_review_completed"])
        transport.assert_not_called()

    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    @patch("run_grounded_generation_v2.make_transport")
    def test_preflight_explains_missing_reviewer_separation(self, transport, evidence):
        env = {"STAGING_ONLY": "true", "AI_GENERATOR_MODEL": "same-model",
               "AI_REVIEWER_MODEL": "same-model", "AI_BLIND_REVIEW_OPT_IN": "true"}
        readiness = execute(object(), ARGS, env)["review_readiness"]
        self.assertEqual(readiness["blind_review"], "reviewer_must_differ")
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
               "AI_PROVIDER_API_KEY": "secret", "AI_GENERATOR_MODEL": "test-model",
               "STAGING_RECEIPT_SIGNING_SECRET": "a" * 48}
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
        transport.assert_called_once_with(
            allowed_hosts=["provider.example"], timeout_seconds=50,
            relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
            relay_secret="a" * 48)
        adapter.assert_called_once_with(
            endpoint=env["AI_PROVIDER_ENDPOINT"], api_key="secret",
            model="test-model", transport=transport.return_value,
            owner_opt_in=True, staging=True)
        generate.assert_called_once()
        # Exercise the callback actually supplied to the pipeline, not only the helper.
        from item_ai_https_transport_v2 import TransportError
        author = generate.call_args.args[3]
        adapter.return_value.side_effect = [TransportError('PROVIDER_RATE_LIMIT', retry_after_seconds=25), {"ok": True}] * 3
        with patch('time.sleep') as sleep:
            for step in ('concept_card', 'item_draft', 'rationale'):
                self.assertEqual(author({"step":step}), {"ok":True})
        self.assertEqual(adapter.return_value.call_count, 6)
        self.assertEqual(sleep.call_count, 3)
        self.assertEqual(sleep.call_args.args, (60,))
        self.assertIsNone(generate.call_args.kwargs["checkpoint"])
        self.assertIsNone(generate.call_args.kwargs["on_checkpoint"])
        self.assertEqual(generate.call_args.kwargs["item_id"], "draft-1")
        self.assertEqual(generate.call_args.kwargs["format"], "MC")
        self.assertEqual(generate.call_args.kwargs["generator_model_id"], "test-model")
        self.assertIsNone(generate.call_args.kwargs["rewrite"])
        self.assertIsNone(generate.call_args.kwargs["review_repair"])
        self.assertIsNone(generate.call_args.kwargs["semantic_lookup"])

    @patch("run_grounded_generation_v2.generate_from_index")
    @patch("run_grounded_generation_v2.make_adapter")
    @patch("run_grounded_generation_v2.make_transport")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_option_reviewer_uses_distinct_model_and_persists_pipeline_report(self, evidence, transport, adapter, generate):
        args=SimpleNamespace(**{**vars(ARGS),"execute":True,"confirm_paid_calls":True})
        env={"STAGING_ONLY":"true","AI_GENERATION_OPT_IN":"true","AI_PROVIDER_ENDPOINT":"https://provider.example/v1/chat/completions",
             "AI_ALLOWED_HOSTS":"provider.example","AI_PROVIDER_API_KEY":"secret","AI_GENERATOR_MODEL":"generator",
             "AI_REVIEWER_MODEL":"reviewer","AI_OPTION_REVIEW_OPT_IN":"true","STAGING_RECEIPT_SIGNING_SECRET":"a"*48}
        generate.return_value={"item_id":"q1","next_state":"draft","source_evidence":{},"item":{},"generator_issues":[],"screening":{"independent_option_adjudication":{"status":"reviewed"}}}
        adapter.return_value.return_value={"judgments":[{"option_id":"A","source_conflict_found":False}]}
        result=execute(object(),args,env)
        callback=generate.call_args.kwargs["option_reviewer"]
        self.assertEqual(generate.call_args.kwargs["option_reviewer_model_id"],"reviewer")
        self.assertIsNone(generate.call_args.kwargs["blind_reviewer"])
        self.assertEqual(callback({"stem":"Which?"}),[{"option_id":"A","source_conflict_found":False,"contradiction_found":False}])
        request=adapter.return_value.call_args.args[0]
        self.assertEqual(request["step"],"option_review"); self.assertTrue(request["blind"])
        self.assertEqual(result["save_payload"]["screening"]["independent_option_adjudication"]["status"],"reviewed")
        self.assertFalse(result["can_publish"])

    @patch("run_grounded_generation_v2.generate_from_index")
    @patch("run_grounded_generation_v2.make_adapter")
    @patch("run_grounded_generation_v2.make_transport")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_trusted_semantic_lookup_is_forwarded(self, evidence, transport, adapter, generate):
        args = SimpleNamespace(**{**vars(ARGS), "execute": True,
                                  "confirm_paid_calls": True})
        env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
               "AI_PROVIDER_ENDPOINT": "https://provider.example/v1/chat/completions",
               "AI_ALLOWED_HOSTS": "provider.example",
               "AI_PROVIDER_API_KEY": "secret", "AI_GENERATOR_MODEL": "test-model",
               "STAGING_RECEIPT_SIGNING_SECRET": "a" * 48}
        generate.return_value = {
            "item_id": "draft-1", "next_state": "needs_editorial_review",
            "source_evidence": {}, "item": {"stem": "Synthetic"},
            "generator_issues": [], "screening": {"can_publish": False}}
        lookup = lambda item: {"embedding": [1.0, 0.0], "neighbors": [],
                               "search_complete": True, "index_id": "test"}
        execute(object(), args, env, semantic_lookup=lookup)
        self.assertIs(generate.call_args.kwargs["semantic_lookup"], lookup)

    @patch("run_grounded_generation_v2.generate_from_index")
    @patch("run_grounded_generation_v2.make_adapter")
    @patch("run_grounded_generation_v2.make_transport")
    @patch("run_grounded_generation_v2.build_evidence", return_value=EVIDENCE)
    def test_explicit_rewrite_opt_in_wires_callable(self, evidence, transport, adapter, generate):
        args = SimpleNamespace(**{**vars(ARGS), "execute": True,
                                  "confirm_paid_calls": True})
        env = {"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true",
               "AI_REWRITE_OPT_IN": "true",
               "AI_PROVIDER_ENDPOINT": "https://provider.example/v1/chat/completions",
               "AI_ALLOWED_HOSTS": "provider.example",
               "AI_PROVIDER_API_KEY": "secret", "AI_GENERATOR_MODEL": "test-model",
               "STAGING_RECEIPT_SIGNING_SECRET": "a" * 48}
        generate.return_value = {
            "item_id": "draft-1", "next_state": "needs_editorial_review",
            "source_evidence": {}, "item": {"stem": "Synthetic"},
            "generator_issues": [], "screening": {"can_publish": False}}
        execute(object(), args, env)
        rewrite = generate.call_args.kwargs["rewrite"]
        self.assertTrue(callable(rewrite))
        self.assertIs(generate.call_args.kwargs["review_repair"], rewrite)
        rewrite({"item": {"status": "draft"}, "issues": [],
                 "max_rewrites": 1, "requires_human_review": True})
        self.assertEqual(adapter.return_value.call_args.args[0]["step"], "rewrite")
        self.assertFalse(adapter.return_value.call_args.args[0]["auto_publish"])
        from item_ai_https_transport_v2 import TransportError
        request={"item":{"status":"draft","evidence":[{"passage_id":"p1","excerpt":"Original quote"}]},
                 "issues":[],"max_rewrites":1,"requires_human_review":True}
        adapter.return_value.reset_mock()
        adapter.return_value.side_effect=[TransportError('PROVIDER_RATE_LIMIT',retry_after_seconds=2),{"evidence":[]}]
        with patch('time.sleep') as sleep:
            rewrite(request)
        sleep.assert_called_once_with(60)
        self.assertEqual(adapter.return_value.call_count,2)
        sent=adapter.return_value.call_args.args[0]
        self.assertNotIn('excerpt',sent['item']['evidence'][0])
        self.assertEqual(sent['trusted_evidence'][0]['passage_id'],'p1')
        self.assertEqual(request['item']['evidence'][0]['excerpt'],'Original quote')
        for error in (TransportError('PROVIDER_TIMEOUT'),TransportError('PROVIDER_RATE_LIMIT'),
                      TransportError('PROVIDER_RATE_LIMIT',retry_after_seconds=61)):
            adapter.return_value.reset_mock()
            adapter.return_value.side_effect=error
            with patch('time.sleep') as sleep, self.assertRaises(TransportError):
                rewrite(request)
            sleep.assert_not_called()
            self.assertEqual(adapter.return_value.call_count,1)

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
