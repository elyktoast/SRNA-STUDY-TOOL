import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from generate_grounded_drafts import generate_drafts

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
ENDPOINT = "https://example.supabase.co/functions/v1/generate-questions"
EVIDENCE = {"material": "[SOURCE 1 | passage_id=p1 | textbook_id=t1 | PDF pages 1-2]\nsource", "sourceName": "book", "citation": "PDF pages",
            "count": 1, "evidence": {"passage_ids": ["p1"], "citation_verified": False}}


class GroundedGenerationTests(unittest.TestCase):
    def call(self, response):
        with patch("generate_grounded_drafts.prepare", return_value=EVIDENCE):
            return generate_drafts(object(), OWNER, "airway", endpoint=ENDPOINT,
                                   jwt="test-token", apikey="test-key", count=1,
                                   transport=lambda url, body, headers: response)

    def test_valid_questions_remain_unapproved(self):
        result = self.call({"questions": [{
            "stem": "Which mechanism?", "options": ["A", "B", "C", "D"],
            "answer": [0], "explanation": "Reason", "type": "single", "sourceExcerpt": "source"}]})
        self.assertEqual(result["count"], 1)
        self.assertFalse(result["autoApproved"])
        self.assertEqual(result["drafts"][0]["candidateSourcePassageIds"], ["p1"])
        self.assertEqual(result["drafts"][0]["sourcePassageIds"], ["p1"])
        self.assertEqual(result["drafts"][0]["sourceExcerptMatch"], "exact")
        self.assertEqual(result["drafts"][0]["evidenceVerificationStatus"], "unverified")
        self.assertTrue(result["drafts"][0]["requiresHumanReview"])

    def test_unmatched_excerpt_is_not_verified(self):
        result = self.call({"questions": [{
            "stem": "Which mechanism?", "options": ["A", "B", "C", "D"],
            "answer": [0], "explanation": "Reason", "type": "single",
            "sourceExcerpt": "invented source claim"}]})
        self.assertEqual(result["drafts"][0]["sourcePassageIds"], [])
        self.assertEqual(result["drafts"][0]["sourceExcerptMatch"], "unmatched")
        self.assertFalse(result["drafts"][0]["citationVerified"])

    def test_rejects_malformed_answer(self):
        with self.assertRaises(ValueError):
            self.call({"questions": [{"stem": "Which?", "options": ["A", "B", "C", "D"],
                                      "answer": [5], "explanation": "Reason"}]})

    def test_rejects_unverified_source_statement(self):
        with self.assertRaisesRegex(ValueError, "source support"):
            self.call({"questions": [{"stem": "Which?", "options": ["A", "B", "C", "D"],
                                      "answer": [0], "explanation": "Reason", "type": "single"}]})

    def test_rejects_insecure_endpoint(self):
        with self.assertRaises(ValueError):
            generate_drafts(object(), OWNER, "airway", endpoint="http://localhost/functions/v1/generate-questions",
                            jwt="token", apikey="key")


if __name__ == "__main__":
    unittest.main()
