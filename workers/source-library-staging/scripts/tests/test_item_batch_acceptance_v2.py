import unittest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from item_batch_acceptance_v2 import accept_generated_batch_draft
from item_explanation_review_v2 import fields_for


class BatchAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.conn = MagicMock()
        self.cursor = self.conn.cursor.return_value.__enter__.return_value
        self.owner, self.draft, self.passage = (str(uuid4()) for _ in range(3))
        self.question = {
            "format": "MC", "key": ["A"],
            "concept_card": {field: "Synthetic condition" for field in
                             ("mechanism", "relevance", "misconception", "counterfactual")},
            "rationale": {field: "Synthetic claim" for field in ("core_concept", "why_key_wins", "trap")},
        }
        stages = {name: {"status":"pass","issues":[]} for name in (
            "schema","deterministic_text","math","evidence","duplicates","blind_model",
            "explanation_evidence","editorial_quality","options_only","independent_option_evidence")}
        stages["duplicates"].update(search_complete=True, index_id="question_semantic_index_v2:@cf/baai/bge-m3:" + "a"*64)
        stages["options_only"]["trials"] = 5
        stages["editorial_quality"]["counterfactual_verification"] = {"status": "pass"}
        stages["explanation_evidence"]["source_support"] = [{
            "fields": [field["label"] for field in fields_for(self.question)],
            "quotes": [{"passage_id":self.passage,"quote":"Synthetic source phrase"}]}]
        self.screening = {"stages":stages, "independent_option_adjudication":{
            "status":"reviewed","issues":[], "judgments":[
                {"option_id":option,"verdict":"supports_key" if option == "A" else "refutes_distractor",
                 "passage_ids":[self.passage],"quotes":["Synthetic source phrase"],"source_conflict_found":False}
                for option in "ABCD"]}}
        self.cursor.fetchone.return_value = self.question, self.screening
        self.cursor.fetchall.return_value = [(self.passage,"Synthetic source phrase")]
        self.saved = {"draft_id":self.draft, "status":"pending_review"}

    def accept(self):
        return accept_generated_batch_draft(self.conn, owner_uid=self.owner, saved=self.saved,
            result={"item":self.question,"screening":self.screening})

    @patch("item_batch_acceptance_v2.review", return_value={"status":"approved_for_bank","published":False})
    @patch("item_batch_acceptance_v2.revalidate", return_value={"issues":[]})
    def test_all_checks_and_current_quotes_accept_into_private_staging_bank(self, validate, review):
        self.assertEqual(self.accept()["status"], "approved_for_bank")
        self.assertIn("No human review recorded",review.call_args.kwargs["notes"])
        validate.assert_called_once()

    @patch("item_batch_acceptance_v2.review")
    def test_held_and_changed_sources_cannot_auto_accept(self, review):
        self.cursor.fetchall.return_value = [(self.passage, "Changed source text")]
        self.assertEqual(self.accept(),self.saved)
        self.screening["stages"]["blind_model"]["status"] = "pending"
        self.assertEqual(self.accept(),self.saved)
        review.assert_not_called()
