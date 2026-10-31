import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run_grounded_generation import run

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"


class RunnerTests(unittest.TestCase):
    def test_default_dry_run_never_calls_ai(self):
        with patch("run_grounded_generation.prepare", return_value={
            "evidence": {"passage_ids": ["p1", "p2"]}, "count": 2
        }), patch("run_grounded_generation.generate_drafts") as generate:
            result = run(object(), OWNER, "airway", count=2)
        generate.assert_not_called()
        self.assertEqual(result["passage_count"], 2)
        self.assertFalse(result["database_writes"])

    def test_explicit_generation_reports_matching_and_unmatched(self):
        with patch("run_grounded_generation.generate_drafts", return_value={
            "count": 2, "drafts": [
                {"sourceExcerptMatch": "exact"},
                {"sourceExcerptMatch": "unmatched"}
            ]
        }):
            result = run(object(), OWNER, "airway", generate=True)
        self.assertEqual(result["exact_excerpt_matches"], 1)
        self.assertEqual(result["unmatched_excerpts"], 1)
        self.assertFalse(result["auto_approved"])
        self.assertFalse(result["database_writes"])


if __name__ == "__main__":
    unittest.main()
