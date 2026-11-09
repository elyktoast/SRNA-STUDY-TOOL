import unittest
from item_option_adjudication_handoff_v2 import run


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.item = {"format": "MC", "stem": "Which?", "options": [
            {"id": "A", "text": "One"}, {"id": "B", "text": "Two"}], "key": ["A"]}
        self.passages = [{"passage_id": "p1", "excerpt": "Source one"},
                         {"passage_id": "p2", "excerpt": "Source two"}]
        self.retrieval = {"all_options_searched": True, "option_audits": [
            {"option_id": "A", "retrieved_passage_ids": ["p1"]},
            {"option_id": "B", "retrieved_passage_ids": ["p2"]}]}

    def test_reviewer_response_is_validated_but_never_published(self):
        def reviewer(request):
            self.assertEqual(request["task"], "independent_option_adjudication")
            return [
                {"option_id": "A", "passage_ids": ["p1"], "verdict": "supports_key",
                 "explanation": "Evidence", "contradiction_found": False},
                {"option_id": "B", "passage_ids": ["p2"], "verdict": "refutes_distractor",
                 "explanation": "Evidence", "contradiction_found": False}]
        report = run(self.item, self.retrieval, reviewer, source_passages=self.passages,
                     generator_model_id="generator", reviewer_model_id="reviewer")
        self.assertEqual(report["status"], "reviewed")
        self.assertFalse(report["clinical_truth_verified"])
        self.assertFalse(report["can_publish"])

    def test_provider_error_is_pending(self):
        def broken(request):
            raise RuntimeError("outage")
        report = run(self.item, self.retrieval, broken, source_passages=self.passages,
                     generator_model_id="generator", reviewer_model_id="reviewer")
        self.assertEqual(report["status"], "pending")

    def test_same_model_is_rejected(self):
        with self.assertRaises(ValueError):
            run(self.item, self.retrieval, lambda request: [], source_passages=self.passages,
                generator_model_id="same", reviewer_model_id="same")


if __name__ == "__main__":
    unittest.main()
