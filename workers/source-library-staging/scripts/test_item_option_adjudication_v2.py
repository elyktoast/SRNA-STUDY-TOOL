import unittest
from item_option_adjudication_v2 import evaluate


class AdjudicationTests(unittest.TestCase):
    def setUp(self):
        self.item = {"format": "MC", "options": [{"id": "A"}, {"id": "B"}], "key": ["A"]}
        self.retrieval = {"option_audits": [
            {"option_id": "A", "retrieved_passage_ids": ["p1"], "search_status": "matches_found"},
            {"option_id": "B", "retrieved_passage_ids": ["p2"], "search_status": "matches_found"}]}
        self.judgments = [
            {"option_id": "A", "passage_ids": ["p1"], "verdict": "supports_key",
             "explanation": "Independent rationale", "contradiction_found": False},
            {"option_id": "B", "passage_ids": ["p2"], "verdict": "refutes_distractor",
             "explanation": "Independent rationale", "contradiction_found": False}]

    def test_complete_adjudication_still_needs_human_review(self):
        result = evaluate(self.item, self.retrieval, self.judgments)
        self.assertEqual(result["status"], "reviewed")
        self.assertFalse(result["clinical_truth_verified"])
        self.assertFalse(result["can_publish"])

    def test_missing_passage_or_contradiction_fails(self):
        self.judgments[1]["passage_ids"] = ["invented"]
        self.judgments[0]["contradiction_found"] = True
        result = evaluate(self.item, self.retrieval, self.judgments)
        self.assertEqual(result["status"], "pending")
        self.assertGreaterEqual(len(result["issues"]), 2)

    def test_missing_option_judgment_rejected(self):
        with self.assertRaises(ValueError):
            evaluate(self.item, self.retrieval, self.judgments[:1])


if __name__ == "__main__":
    unittest.main()
