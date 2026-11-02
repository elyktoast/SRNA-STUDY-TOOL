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
    domain="III", section="III.H", objective="III.H.4", item_id="draft-1")
EVIDENCE = {"topic": "airway", "evidence_count": 1,
            "can_generate_grounded_questions": True, "sources": [{"passage_id": "p1"}]}

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
