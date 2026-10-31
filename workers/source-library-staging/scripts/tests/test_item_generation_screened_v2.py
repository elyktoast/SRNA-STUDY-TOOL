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
    @patch("item_generation_screened_v2.generate_one")
    def test_generator_issues_block_intake(self, generate):
        generate.return_value = {"item": {"item_id": "new-1"},
                                 "schema_issues": [{"rule_id": "R-12.4", "message": "bad citation"}]}
        result = generate_and_screen(None, **ARGS)
        self.assertIsNone(result["screening"])
        self.assertEqual(result["next_state"], "needs_source_review")
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
