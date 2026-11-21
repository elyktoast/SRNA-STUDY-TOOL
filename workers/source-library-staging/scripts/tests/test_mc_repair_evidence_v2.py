import unittest
from types import SimpleNamespace
from unittest.mock import patch
from item_mc_repair_evidence_v2 import supplement

class RepairEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.args = SimpleNamespace(owner_uid="owner", textbook_id="book1", textbook_ids=["book1", "book2"],
                                    section_id=None, include_subsections=False, page_start=None, page_end=None)
        self.item = {"evidence": [{"passage_id": "original"}], "options": [
            {"id": "A", "text": "Method alpha"}, {"id": "B", "text": "Method beta"},
            {"id": "C", "text": "Method gamma"}, {"id": "D", "text": "Method delta"}]}

    @patch("item_mc_repair_evidence_v2.build_evidence")
    def test_searches_only_source_held_options_with_original_book_scope(self, search):
        def packet(conn, owner, query, **scope):
            return {"sources": [{"passage_id": query + scope["textbook_id"], "textbook_id": scope["textbook_id"]}]}
        search.side_effect = packet
        issues = [{"rule_id": "R-2.4", "field": "rationale.distractor_breakdown.B"},
                  {"rule_id": "R-2.4", "field": "distractor_evidence.B"},
                  {"rule_id": "R-12.4", "option_id": "D"}]
        result = supplement(object(), self.args, self.item, issues)
        self.assertEqual(len(search.call_args_list), 4)
        self.assertEqual([p["passage_id"] for p in result],
                         ["Method betabook1", "Method deltabook1", "Method betabook2", "Method deltabook2"])
        self.assertTrue(all(call.args[1] == "owner" and call.kwargs["limit"] == 2
                            for call in search.call_args_list))

    @patch("item_mc_repair_evidence_v2.build_evidence")
    def test_preserves_physical_scope_and_ignores_foreign_duplicate_or_existing_passages(self, search):
        self.args.textbook_ids = None
        self.args.section_id = "section"
        self.args.include_subsections = True
        self.args.page_start, self.args.page_end = 3, 8
        search.return_value = {"sources": [
            {"passage_id": "original", "textbook_id": "book1"},
            {"passage_id": "foreign", "textbook_id": "other"},
            {"passage_id": "new", "textbook_id": "book1"}]}
        result = supplement(object(), self.args, self.item,
                            [{"rule_id": "R-2.4", "field": "distractor_evidence.C"}])
        self.assertEqual([p["passage_id"] for p in result], ["new"])
        self.assertEqual(search.call_args.kwargs,
                         {"textbook_id": "book1", "limit": 2, "section_id": "section",
                          "include_subsections": True, "page_start": 3, "page_end": 8})

    @patch("item_mc_repair_evidence_v2.build_evidence")
    def test_counterfactual_source_failure_fetches_positive_peer_definitions(self, search):
        self.item["key"] = ["A"]
        search.side_effect = lambda conn, owner, query, **scope: {"sources": [
            {"passage_id": query + scope["textbook_id"], "textbook_id": scope["textbook_id"]}]}
        result = supplement(object(), self.args, self.item,
            [{"rule_id":"R-2.4", "field":"concept_card.counterfactual"}])
        self.assertEqual({call.args[2] for call in search.call_args_list},
                         {"Method beta", "Method gamma", "Method delta"})
        self.assertEqual(len(result),4)
        self.assertEqual([p["passage_id"] for p in result[:3]],
                         ["Method betabook1", "Method gammabook1", "Method deltabook1"])
        self.assertTrue(all(call.args[1] == "owner" for call in search.call_args_list))

    @patch("item_mc_repair_evidence_v2.build_evidence")
    def test_non_source_or_non_option_issues_do_not_search(self, search):
        for issues in ([], [{"rule_id": "R-12.2", "field": "options"}],
                       [{"rule_id": "R-2.4", "field": "concept_card.mechanism"}]):
            self.assertEqual(supplement(object(), self.args, self.item, issues), [])
        search.assert_not_called()
