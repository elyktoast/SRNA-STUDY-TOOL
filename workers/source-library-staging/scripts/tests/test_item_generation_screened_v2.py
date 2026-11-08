import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_screened_v2 import generate_and_screen

ARGS = dict(mode="NCE", domain="III", section="H", objective="III.H.4",
            evidence=[{"passage_id": "p1", "textbook_id": "t1",
                       "excerpt": "Trusted source", "pdf_page_start": 12}],
            item_id="new-1")

class ScreenedGenerationTests(unittest.TestCase):
    @patch("item_generation_screened_v2.intake")
    def test_real_three_step_generator_hands_off_to_screening(self, intake):
        from test_item_standard_v2 import sample
        calls = []
        def adapter(request):
            calls.append(request["step"])
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                draft = sample()
                draft["evidence"] = [{"textbook_id": "t1", "passage_id": "p1",
                                      "pdf_page": 12, "excerpt": "Trusted source"}]
                draft["distractor_evidence"] = {
                    option["id"]: {
                        "verdict": "supports_key" if option["id"] == "A" else "refutes_distractor",
                        "passage_ids": ["p1"],
                        "explanation": "Linked to trusted indexed passage",
                    } for option in draft["options"]
                }
                return draft
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"A": "correct", "B": "wrong", "C": "wrong", "D": "wrong"})
        intake.return_value = {"draft_reviews": [{"status": "draft",
                                                  "screening": {"stages": {"human_review": {"status": "pending"}}}}]}
        result = generate_and_screen(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        self.assertEqual(result["generator_issues"], [], result["generator_issues"])
        intake.assert_called_once()
        self.assertIsNotNone(result["screening"])
        submitted = intake.call_args.args[0]["questions"][0]
        self.assertEqual(submitted["item_id"], "new-1")
        self.assertEqual(submitted["status"], "draft")
        self.assertEqual(submitted["evidence"][0]["pdf_page"], 12)
        self.assertEqual(intake.call_args.kwargs["passages"]["p1"]["text"], "Trusted source")
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_no_semantic_index_never_counts_as_duplicate_pass(self, generate, intake):
        generate.return_value = {"item": {"item_id": "new-1"}, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{"status": "draft", "screening": {
            "stages": {"duplicates": {"status": "pass", "issues": []},
                       "blind_model": {"status": "pending", "issues": []}},
            "screening_complete": True}}]}
        result = generate_and_screen(None, **ARGS)
        self.assertEqual(result["screening"]["stages"]["duplicates"]["status"], "pending")
        self.assertIn("duplicates", result["screening"]["pending_verifications"])
        self.assertFalse(result["screening"]["screening_complete"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_pending_verifications_are_explicit(self, generate, intake):
        generate.return_value = {"item": {"item_id": "new-1"}, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{
            "status": "draft", "screening": {
                "stages": {
                    "evidence": {"status": "pass", "issues": []},
                    "duplicates": {"status": "pending", "issues": []},
                    "blind_model": {"status": "pending", "issues": []},
                    "human_review": {"status": "pending", "issues": []},
                }
            }
        }]}
        result = generate_and_screen(None, **ARGS)
        self.assertEqual(result["screening"]["pending_verifications"],
                         ["duplicates", "blind_model"])
        self.assertFalse(result["screening"]["screening_complete"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_post_generation_semantic_lookup_passes_vectors(self, generate, intake):
        item = {"item_id": "new-1", "stem": "Test"}
        generate.return_value = {"item": item, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{
            "status": "draft", "screening": {"stages": {
                "duplicates": {"status": "pass", "issues": []},
                "blind_model": {"status": "pending", "issues": []}}}}]}
        seen = []
        def lookup(candidate):
            seen.append(candidate)
            return {"embedding": [1.0, 0.0], "neighbors": [
                {"item_id": "existing-1", "embedding": [0.9, 0.1]}],
                "search_complete": True, "index_id": "staging-v1"}
        result = generate_and_screen(None, **ARGS, semantic_lookup=lookup)
        self.assertEqual(seen, [item])
        self.assertEqual(intake.call_args.kwargs["embeddings"]["new-1"], [1.0, 0.0])
        self.assertEqual(intake.call_args.kwargs["neighbors"][0]["item_id"], "existing-1")
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_semantic_lookup_failure_remains_pending(self, generate, intake):
        generate.return_value = {"item": {"item_id": "new-1"}, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{
            "status": "draft", "screening": {"stages": {
                "duplicates": {"status": "pass", "issues": []},
                "blind_model": {"status": "pending", "issues": []}}}}]}
        def unavailable(item):
            raise RuntimeError("search unavailable")
        result = generate_and_screen(None, **ARGS, semantic_lookup=unavailable)
        self.assertEqual(result["screening"]["stages"]["duplicates"]["status"], "pending")
        self.assertIn("duplicates", result["screening"]["pending_verifications"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_incomplete_semantic_search_never_passes(self, generate, intake):
        generate.return_value = {"item": {"item_id": "new-1"}, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{"status": "draft",
            "screening": {"stages": {"duplicates": {"status": "pass"},
                                      "blind_model": {"status": "pending"}}}}]}
        def lookup(item):
            return {"embedding": [1.0, 0.0], "neighbors": [],
                    "search_complete": False, "index_id": "staging-v1"}
        result = generate_and_screen(None, **ARGS, semantic_lookup=lookup)
        self.assertEqual(result["screening"]["stages"]["duplicates"]["status"], "pending")
        self.assertIn("duplicates", result["screening"]["pending_verifications"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.generate_one")
    def test_partial_semantic_inputs_rejected_before_paid_generation(self, generate):
        with self.assertRaisesRegex(ValueError, "both candidate embedding and neighbors"):
            generate_and_screen(None, **ARGS, embedding=[0.1, 0.2])
        with self.assertRaisesRegex(ValueError, "both candidate embedding and neighbors"):
            generate_and_screen(None, **ARGS, neighbors=[])
        generate.assert_not_called()

    @patch("item_generation_screened_v2.generate_one")
    def test_reviewer_same_model_rejected_early(self, generate):
        with self.assertRaises(ValueError):
            generate_and_screen(None, **ARGS, blind_reviewer=lambda request: {},
                                generator_model_id="same", reviewer_model_id="same")
        generate.assert_not_called()

    @patch("item_generation_screened_v2.attempt_once")
    @patch("item_generation_screened_v2.generate_one")
    def test_optional_rewrite_is_bounded_and_revalidated(self, generate, attempt):
        original = {"item_id": "new-1", "status": "draft"}
        generate.return_value = {"item": original,
                                 "schema_issues": [{"rule_id": "R-2.5", "message": "citation"}]}
        attempt.return_value = {"item": original,
                                "issues": [{"rule_id": "R-2.5", "message": "still missing"}],
                                "rewrite_attempts": 1}
        result = generate_and_screen(None, **ARGS, rewrite=lambda request: original)
        attempt.assert_called_once()
        self.assertTrue(callable(attempt.call_args.args[3]))
        self.assertEqual(result["next_state"], "needs_source_review")
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.generate_one")
    def test_generator_issues_block_intake(self, generate):
        generate.return_value = {"item": {"item_id": "new-1"},
                                 "schema_issues": [{"rule_id": "R-2.5", "message": "bad citation"}]}
        result = generate_and_screen(None, **ARGS)
        self.assertIsNotNone(result["screening"])
        self.assertFalse(result["screening"]["can_publish"])
        self.assertIn("blind_model", result["screening"]["pending_verifications"])
        self.assertEqual(result["next_state"], "needs_source_review")
        self.assertFalse(result["can_publish"])
    @patch("item_generation_screened_v2.generate_one")
    def test_clang_failure_is_editorial_not_source(self, generate):
        generate.return_value = {"item": {"item_id": "new-1"},
                                 "schema_issues": [{"rule_id": "R-12.4", "message": "Clang detected"}]}
        result = generate_and_screen(None, **ARGS)
        self.assertEqual(result["next_state"], "needs_editorial_review")
        self.assertEqual(result["screening"]["stages"]["evidence"]["status"], "pending")

    @patch("item_generation_screened_v2.generate_one")
    def test_all_five_formats_reject_invalid_generator_output_before_screening(self, generate):
        for format_name in ("MC", "MS", "SA", "DD", "HS"):
            with self.subTest(format=format_name):
                generate.return_value = {
                    "item": {"item_id": "new-1", "format": format_name},
                    "schema_issues": [{"rule_id": "R-17", "message": "unsupported source"}],
                }
                result = generate_and_screen(None, **ARGS, format=format_name)
                self.assertEqual(generate.call_args.kwargs["format"], format_name)
                self.assertEqual(result["next_state"], "needs_source_review")
                self.assertIsNotNone(result["screening"])
                self.assertFalse(result["screening"]["can_publish"])
                self.assertTrue(result["requires_human_review"])
                self.assertFalse(result["can_publish"])
                self.assertFalse(result["database_writes"])

    @patch("item_generation_screened_v2.attach_blind")
    @patch("item_generation_screened_v2.blind_review")
    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_explicit_blind_reviewer_handoff(self, generate, intake, blind, attach):
        item = {"item_id": "new-1", "stem": "Clinical question"}
        generated_screening = {"stages": {"blind_model": {"status": "pending"},
                                          "human_review": {"status": "pending"}}}
        generate.return_value = {"item": item, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{"status": "draft",
                                                 "screening": generated_screening}]}
        blind.return_value = {"status": "pass", "issues": []}
        attach.return_value = {"next_state": "draft", "stages": generated_screening["stages"],
                               "can_publish": False}
        reviewer = lambda request: {"choice": "A"}
        result = generate_and_screen(None, **ARGS, blind_reviewer=reviewer,
                                     generator_model_id="generator-v1",
                                     reviewer_model_id="reviewer-v2")
        blind.assert_called_once_with(item, reviewer, generator_model_id="generator-v1",
                                      reviewer_model_id="reviewer-v2")
        attach.assert_called_once_with(generated_screening, blind.return_value)
        self.assertEqual(result["screening"]["next_state"], "draft")
        self.assertFalse(result["screening"]["can_publish"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.blind_review", side_effect=RuntimeError("offline"))
    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_blind_outage_keeps_unpublished_draft(self, generate, intake, blind):
        generate.return_value = {"item": {"item_id": "new-1"}, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{
            "status": "draft", "screening": {"stages": {
                "blind_model": {"status": "pending", "issues": []},
                "human_review": {"status": "pending", "issues": []}}}}]}
        result = generate_and_screen(None, **ARGS, blind_reviewer=lambda request: {},
                                     generator_model_id="generator-v1",
                                     reviewer_model_id="reviewer-v2")
        self.assertEqual(result["item"]["item_id"], "new-1")
        self.assertIn("blind_model", result["screening"]["pending_verifications"])
        self.assertFalse(result["screening"]["screening_complete"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.generate_one")
    def test_clean_generator_routes_to_screening(self, generate, intake):
        generate.return_value = {"item": {"item_id": "new-1"}, "schema_issues": []}
        intake.return_value = {"draft_reviews": [{"status": "draft",
                                                 "screening": {"stages": {"human_review": {"status": "pending"}}}}]}
        result = generate_and_screen(None, **ARGS)
        self.assertEqual(result["next_state"], "draft")
        self.assertFalse(result["can_publish"])
        self.assertEqual(intake.call_args.kwargs["passages"]["p1"]["text"], "Trusted source")

if __name__ == "__main__":
    unittest.main()
