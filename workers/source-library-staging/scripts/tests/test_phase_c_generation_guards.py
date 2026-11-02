"""Phase C safety regression tests; no network, database, or paid model calls."""
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_runner_v2 import generate_one


class GenerationGuardTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.passage = {"passage_id": "p-1", "textbook_id": "book-1", "excerpt": "Illustrative source text"}
        self.kw = dict(mode="NCE", domain="III", section="H", objective="III.H.4",
                       evidence=[self.passage], format="MC", item_id="draft-1")

    def adapter(self, request):
        self.calls.append(request["step"])
        return {"objective": "III.H.5", "mechanism": "mechanism",
                "relevance": "relevance", "misconception": "misconception",
                "counterfactual": "counterfactual", "evidence_ids": ["p-1"]}

    def test_rejects_unsupported_format_before_ai_call(self):
        with self.assertRaisesRegex(ValueError, "Unsupported v2.0"):
            generate_one(self.adapter, **{**self.kw, "format": "TRUE_FALSE"})
        self.assertEqual(self.calls, [])

    def test_rejects_malformed_concept_card_before_draft(self):
        def malformed(request):
            self.calls.append(request["step"])
            return {"objective": "III.H.4", "mechanism": ["not text"],
                    "relevance": "relevance", "misconception": "misconception",
                    "counterfactual": "counterfactual", "evidence_ids": ["p-1"]}
        with self.assertRaisesRegex(ValueError, "Concept card incomplete"):
            generate_one(malformed, **self.kw)
        self.assertEqual(self.calls, ["concept_card"])

    def test_rejects_missing_evidence_before_ai_call(self):
        with self.assertRaisesRegex(ValueError, "Verified indexed evidence"):
            generate_one(self.adapter, **{**self.kw, "evidence": []})
        self.assertEqual(self.calls, [])

    def test_rejects_duplicate_passages_before_ai_call(self):
        with self.assertRaisesRegex(ValueError, "Duplicate passage IDs"):
            generate_one(self.adapter, **{**self.kw, "evidence": [self.passage, dict(self.passage)]})
        self.assertEqual(self.calls, [])

    def test_rejects_mismatched_blueprint_objective_before_draft(self):
        with self.assertRaisesRegex(ValueError, "blueprint objective"):
            generate_one(self.adapter, **self.kw)
        self.assertEqual(self.calls, ["concept_card"])


if __name__ == "__main__":
    unittest.main()
