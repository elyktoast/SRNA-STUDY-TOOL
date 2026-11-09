import copy
import unittest
from unittest.mock import patch
from item_explanation_review_v2 import review, fields_for
from item_generation_screened_v2 import generate_and_screen


class ExplanationReviewTests(unittest.TestCase):
    def setUp(self):
        self.item = {"evidence":[{"passage_id":"p1"}],
                     "concept_card":{k:"Classification statement" for k in ("mechanism","relevance","misconception","counterfactual")},
                     "rationale":{**{k:"Classification statement" for k in ("core_concept","why_key_wins","trap")},
                                  "distractor_breakdown":{"A":"Classification statement"}}}
        self.sources = [{"passage_id":"p1","excerpt":"Triggering agents.\nVolatile anesthetics."}]
        self.ids = [f["id"] for f in fields_for(self.item)]
        self.response = {"supported_groups":[{"field_ids":self.ids,
                         "quote_refs":[{"passage_id":"p1","span_id":"q1"}]}],"unsupported":[]}

    def test_complete_field_coverage_restores_exact_cited_source_without_approval(self):
        calls = []
        def reviewer(payload):
            calls.append(payload)
            return self.response
        report = review(self.item, self.sources, reviewer)
        self.assertEqual(report["status"], "pass")
        self.assertEqual(len(report["checked_fields"]), 8)
        self.assertEqual(report["source_support"][0]["quotes"][0]["quote"], "Volatile anesthetics.")
        self.assertFalse(report["can_publish"])
        self.assertFalse(report["clinical_truth_verified"])
        self.assertTrue(report["human_review_required"])
        self.assertNotIn("key", calls[0])
        self.assertNotIn("blind", calls[0])

    def test_unsupported_mechanism_targets_existing_rewrite_field(self):
        response = copy.deepcopy(self.response)
        response["supported_groups"][0]["field_ids"] = self.ids[1:]
        response["unsupported"] = [{"field_id":"e0","reason":"The classification does not establish receptor physiology."}]
        result = review(self.item, self.sources, lambda p:response)
        self.assertEqual(result["status"], "flag")
        self.assertEqual(result["issues"][0]["field"], "concept_card.mechanism")
        self.assertEqual(result["issues"][0]["rule_id"], "R-2.4")

    def test_missing_repeated_unknown_or_uncited_support_never_passes(self):
        for change in ("missing", "duplicate", "unknown_field", "unknown_span", "uncited"):
            response = copy.deepcopy(self.response)
            group = response["supported_groups"][0]
            if change == "missing": group["field_ids"].pop()
            if change == "duplicate": group["field_ids"].append("e0")
            if change == "unknown_field": group["field_ids"].append("invented")
            if change == "unknown_span": group["quote_refs"][0]["span_id"] = "missing"
            if change == "uncited": group["quote_refs"][0]["passage_id"] = "p2"
            with self.subTest(change=change):
                result = review(self.item, self.sources + [{"passage_id":"p2","excerpt":"Other evidence."}], lambda p:response)
                self.assertEqual(result["status"], "pending")

    def test_adapter_bounds_output_and_rejects_answer_or_approval_envelopes(self):
        import json
        from item_ai_provider_v2 import make_adapter
        from item_source_quote_spans_v2 import prepare
        calls=[]
        def transport(**kwargs):
            calls.append(kwargs)
            return {"choices":[{"message":{"content":json.dumps(self.response)}}]}
        adapter=make_adapter(endpoint="https://provider.example/v1",api_key="test",model="reviewer",
                             transport=transport,owner_opt_in=True)
        packet,_=prepare({"source_passages":self.sources})
        request={"step":"explanation_review","rules_version":"2.0","auto_publish":False,
                 "independent":True,"fields":[{**f,"passage_ids":["p1"]} for f in fields_for(self.item)],"source_passages":packet["source_passages"]}
        for extra in ({"key":["A"]},{"can_publish":True},{"independent":False}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                adapter({**request,**extra})
        self.assertEqual(calls,[])
        adapter(request)
        self.assertEqual(calls[0]["body"]["max_tokens"],1000)
        self.assertNotIn("key",json.loads(calls[0]["body"]["messages"][1]["content"]))

    def test_provider_outage_preserves_pending_without_clinical_approval(self):
        def broken(payload): raise TimeoutError("private provider text")
        result = review(self.item, self.sources, broken)
        self.assertEqual(result["status"], "pending")
        self.assertNotIn("private", str(result))
        self.assertFalse(result["can_publish"])


class ExplanationRepairTests(unittest.TestCase):
    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.attempt_once")
    @patch("item_generation_screened_v2.generate_one")
    def test_unsupported_text_rewrites_once_then_rechecks(self, generate, repair, intake):
        original = {"item_id":"new-1", "status":"draft", "format":"MC"}
        revised = {**original, "fixed":True}
        generate.return_value = {"item":original,"schema_issues":[]}
        repair.return_value = {"item":revised,"issues":[],"rewrite_attempts":1}
        intake.return_value = {"draft_reviews":[{"status":"draft","screening":{"stages":{}}}]}
        issue = {"rule_id":"R-2.4","field":"concept_card.mechanism","message":"Unsupported physiology"}
        base = {"can_publish":False,"clinical_truth_verified":False,"human_review_required":True}
        calls = []
        def explanation(item):
            calls.append(item)
            return {**base,"status":"pass" if item.get("fixed") else "flag",
                    "issues":[] if item.get("fixed") else [issue]}
        result = generate_and_screen(lambda r:{}, mode="NCE",domain="III",section="H",objective="III.H.4",
            item_id="new-1", evidence=[{"passage_id":"p1","textbook_id":"t1","excerpt":"Source","pdf_page_start":1}],
            rewrite=lambda r:{}, explanation_review=explanation)
        self.assertEqual(len(calls), 2)
        repair.assert_called_once()
        self.assertEqual(repair.call_args.args[1], [issue])
        self.assertEqual(result["screening"]["stages"]["explanation_evidence"]["status"], "pass")
        self.assertEqual(result["screening"]["rewrite_attempts_used"], 1)
        self.assertEqual(result["screening"]["rewrite_attempts_allowed"], 0)
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.attempt_once")
    @patch("item_generation_screened_v2.generate_one")
    def test_unavailable_review_does_not_spend_rewrite(self, generate, repair, intake):
        generate.return_value = {"item":{"item_id":"new-1"},"schema_issues":[]}
        intake.return_value = {"draft_reviews":[{"status":"draft","screening":{"stages":{}}}]}
        def unavailable(item): raise TimeoutError()
        result = generate_and_screen(lambda r:{},mode="NCE",domain="III",section="H",objective="III.H.4",
            item_id="new-1", evidence=[{"passage_id":"p1","textbook_id":"t1","excerpt":"Source","pdf_page_start":1}],
            rewrite=lambda r:{}, explanation_review=unavailable)
        repair.assert_not_called()
        self.assertIn("explanation_evidence",result["screening"]["pending_verifications"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.attempt_once")
    @patch("item_generation_screened_v2.generate_one")
    def test_second_unsupported_result_stays_flagged_after_one_attempt(self, generate, repair):
        generate.return_value={"item":{"item_id":"new-1"},"schema_issues":[]}
        repair.return_value={"item":{"item_id":"new-1"},"issues":[],"rewrite_attempts":1}
        issue={"rule_id":"R-2.4","message":"Unsupported claim"}
        result=generate_and_screen(lambda r:{},mode="NCE",domain="III",section="H",objective="III.H.4",
            item_id="new-1",evidence=[{"passage_id":"p1","textbook_id":"t1","excerpt":"Source","pdf_page_start":1}],
            rewrite=lambda r:{},explanation_review=lambda i:{"status":"flag","issues":[issue],"can_publish":False,
                "clinical_truth_verified":False,"human_review_required":True})
        repair.assert_called_once()
        self.assertEqual(result["screening"]["stages"]["explanation_evidence"]["status"],"flag")
        self.assertEqual(result["rewrite_attempts_used"],1)
        self.assertFalse(result["can_publish"])
