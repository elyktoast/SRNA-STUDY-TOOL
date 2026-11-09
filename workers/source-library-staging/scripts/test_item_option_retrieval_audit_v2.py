import unittest
from unittest.mock import patch
from item_option_retrieval_audit_v2 import audit


class OptionRetrievalAuditTests(unittest.TestCase):
    def test_each_option_is_searched_and_remains_unverified(self):
        item = {"format": "MC", "stem": "Which effect is expected?",
                "options": [{"id": "A", "text": "Vasodilation"},
                            {"id": "B", "text": "Vasoconstriction"}],
                "key": ["A"]}
        calls = []

        def fake_search(conn, query, owner, *, limit, textbook_id):
            calls.append((query, owner, limit, textbook_id))
            return [{"passage_id": "passage-" + str(len(calls))}]

        with patch("item_option_retrieval_audit_v2.search", side_effect=fake_search):
            result = audit(object(), "owner", item, textbook_id="book")
        self.assertEqual(len(calls), 2)
        self.assertEqual([r["expected_verdict"] for r in result["option_audits"]],
                         ["supports_key", "refutes_distractor"])
        self.assertFalse(result["clinical_verification_complete"])
        self.assertFalse(result["can_publish"])
        self.assertTrue(all(not r["contradiction_checked"] for r in result["option_audits"]))

    def test_missing_evidence_is_not_a_verified_refutation(self):
        item = {"format": "MC", "stem": "Which effect?", "options":
                [{"id": "A", "text": "Alpha"}, {"id": "B", "text": "Beta"}],
                "key": ["A"]}
        with patch("item_option_retrieval_audit_v2.search", return_value=[]):
            result = audit(object(), "owner", item, textbook_id="book")
        self.assertTrue(result["all_options_searched"])
        self.assertFalse(result["all_options_have_matches"])
        self.assertFalse(result["clinical_verification_complete"])

    def test_search_error_is_not_silently_counted_as_success(self):
        item = {"format": "MC", "stem": "Which effect?", "options":
                [{"id": "A", "text": "Alpha"}], "key": ["A"]}
        with patch("item_option_retrieval_audit_v2.search", side_effect=RuntimeError("offline")):
            result = audit(object(), "owner", item, textbook_id="book")
        self.assertFalse(result["all_options_searched"])
        self.assertEqual(result["option_audits"][0]["search_status"], "failed")

    def test_rejects_incomplete_option(self):
        with self.assertRaises(ValueError):
            audit(None, "owner", {"format": "MC", "stem": "Question",
                                   "options": [{"id": "A"}], "key": ["A"]},
                  textbook_id="book")


if __name__ == "__main__":
    unittest.main()
