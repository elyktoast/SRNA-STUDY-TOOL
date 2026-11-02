import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from board_item_quality import NCE_DOMAINS, REASONING_TARGETS, DIFFICULTY_TARGETS, blueprint_counts, review_item


class BoardQualityTests(unittest.TestCase):
    def test_nce_domain_allocation(self):
        self.assertEqual(blueprint_counts(100, NCE_DOMAINS),
                         {"basic_sciences": 20, "equipment_instrumentation_technology": 20,
                          "general_principles_of_anesthesia": 35,
                          "surgical_procedures_special_populations": 25})
        for weights in (NCE_DOMAINS, REASONING_TARGETS, DIFFICULTY_TARGETS):
            for n in (1, 3, 7, 17, 100, 170):
                self.assertEqual(sum(blueprint_counts(n, weights).values()), n)

    def test_draft_not_automatically_approved(self):
        item = {"stem": "Which mechanism?", "type": "single",
                "options": ["A", "B", "C", "D"], "answer": [0],
                "sourceExcerpt": "evidence", "sourceExcerptMatch": "exact",
                "citationVerified": True, "evidenceVerificationStatus": "verified",
                "nceDomain": "basic_sciences",
                "reasoningCategory": "physiology_pharmacology_integration",
                "difficultyTier": "advanced",
                "explanation": " ".join((
                    "The Core Concept:", "Why the Correct Answer Wins:",
                    "The Trap Identified:", "Distractor Breakdown:"))}
        result = review_item(item)
        self.assertEqual(result["errors"], [])
        self.assertFalse(result["eligible_for_approval"])
        self.assertIn("independent_blind_review", result["pending_review"])
        self.assertIn("Duplicate stem", review_item(item, known_stems=["which mechanism?"])["errors"])

    def test_missing_evidence_flagged(self):
        result = review_item({"stem": "What is correct?", "type": "single",
                              "options": ["A", "B", "C", "D"], "answer": [0]})
        self.assertIn("Source excerpt not matched to indexed passage", result["errors"])
        self.assertIn("Source evidence not independently verified", result["errors"])


if __name__ == "__main__":
    unittest.main()
