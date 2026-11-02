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
                return draft
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        intake.return_value = {"draft_reviews": [{"status": "draft",
                                                  "screening": {"stages": {"human_review": {"status": "pending"}}}}]}
        result = generate_and_screen(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        if result["generator_issues"]:
            self.assertIsNone(result["screening"])
            self.assertFalse(intake.called)
        else:
            intake.assert_called_once()
            self.assertIsNotNone(result["screening"])
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])

    @patch("item_generation_screened_v2.generate_one")
    def test_generator_issues_block_intake(self, generate):
        generate.return_value = {"item": {"item_id": "new-1"},
                                 "schema_issues": [{"rule_id": "R-12.4", "message": "bad citation"}]}
        result = generate_and_screen(None, **ARGS)
        self.assertIsNone(result["screening"])
        self.assertEqual(result["next_state"], "needs_source_review")
        self.assertFalse(result["can_publish"])
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
                self.assertIsNone(result["screening"])
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
        self.assertEqual(result["screening"], attach.return_value)
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
