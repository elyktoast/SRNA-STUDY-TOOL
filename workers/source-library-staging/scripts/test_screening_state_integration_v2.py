"""Offline integration tests: blocked screening must not masquerade as a pass."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parent))
from item_generation_screened_v2 import generate_and_screen


class ScreeningStateTests(unittest.TestCase):
    def run_failed(self, issues, rewrite=None):
        item = {"item_id": "saved-intubation-regression", "format": "MC", "key": ["C"],
                "status": "draft", "concept_card": {"evidence_ids": ["p49"]}}
        evidence = [{"passage_id": "p49", "textbook_id": "book", "excerpt": "indexed text"}]
        generated = {"item": item, "schema_issues": issues}
        with patch("item_generation_screened_v2.generate_one", return_value=generated):
            return generate_and_screen(lambda _: {}, mode="NCE", domain="I",
                                       section="A", objective="I.A.1", evidence=evidence,
                                       item_id=item["item_id"], rewrite=rewrite)

    def test_schema_failure_blocks_downstream(self):
        result = self.run_failed([{"rule_id": "R-15", "message": "Missing field"}])
        stages = result["screening"]["stages"]
        self.assertEqual(stages["schema"]["status"], "fail")
        self.assertEqual(stages["duplicates"]["blocked_by"], "schema")
        self.assertEqual(stages["blind_model"]["blocked_by"], "schema")
        self.assertFalse(result["can_publish"])

    def test_source_failure_preserves_evidence_failure(self):
        result = self.run_failed([{"rule_id": "R-2.5", "message": "Source mismatch"}])
        self.assertEqual(result["screening"]["stages"]["evidence"]["status"], "fail")
        self.assertEqual(result["next_state"], "needs_source_review")

    def test_rewrite_outage_retains_original_diagnostics(self):
        def outage(_):
            raise RuntimeError("provider outage")
        result = self.run_failed([{"rule_id": "R-15", "message": "Missing field"}], rewrite=outage)
        screening = result["screening"]
        self.assertEqual(screening["rewrite_attempts_used"], 1)
        self.assertEqual(screening["rewrite_attempts_allowed"], 0)
        self.assertEqual(screening["rewrite_original_issues"], screening["rewrite_revised_issues"])
        self.assertFalse(screening["screening_complete"])


if __name__ == "__main__":
    unittest.main()
