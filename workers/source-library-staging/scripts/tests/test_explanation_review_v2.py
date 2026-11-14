import copy
import unittest
from unittest.mock import patch
from item_explanation_review_v2 import review, fields_for
from item_generation_screened_v2 import generate_and_screen


class ExplanationReviewTests(unittest.TestCase):
    def test_counterfactual_source_review_checks_clinical_premises_not_answer_letters(self):
        self.item["concept_card"]["counterfactual"]='If "condition X" is replaced by "condition Y", the best response changes to option(s) A.'
        text=next(f["text"] for f in fields_for(self.item) if f["label"]=="concept_card.counterfactual")
        self.assertIn("condition X",text);self.assertIn("condition Y",text)
        self.assertNotIn("option",text)
        self.item["concept_card"]["counterfactual"] += " Additional unsupported clinical assertion."
        text=next(f["text"] for f in fields_for(self.item) if f["label"]=="concept_card.counterfactual")
        self.assertIn("Additional unsupported clinical assertion",text)
        self.assertIn("option(s) A",text)

    def test_reviewer_pass_cannot_turn_source_silence_into_disproof(self):
        self.item["rationale"]["distractor_breakdown"]["A"]="Incorrect because the source does not mention this effect."
        report=review(self.item,self.sources,lambda p:self.response)
        self.assertEqual(report["status"],"flag")
        self.assertIn("rationale.distractor_breakdown.A",[x["field"] for x in report["issues"]])
        self.assertNotIn("rationale.distractor_breakdown.A",[f for g in report["source_support"] for f in g["fields"]])
        self.item["rationale"]["distractor_breakdown"]["A"]="The patient has no evidence of obstruction; the source states the relevant classification."
        self.assertEqual(review(self.item,self.sources,lambda p:self.response)["status"],"pass")

    def test_mixed_citation_scopes_are_separated_before_model_grouping(self):
        self.item["evidence"].append({"passage_id":"p2"})
        self.sources.append({"passage_id":"p2","excerpt":"Second source.\nSeparate evidence statement."})
        self.item["concept_card"]["evidence_ids"]=["p1","p2"]
        self.item["distractor_evidence"]={"A":{"explanation":"Option claim", "passage_ids":["p2"]}}
        calls=[]
        def reviewer(payload):
            calls.append(payload)
            scopes={tuple(f["passage_ids"]) for f in payload["fields"]}
            self.assertEqual(len(scopes),1)
            pid=payload["fields"][0]["passage_ids"][0]
            return {"supported_groups":[{"field_ids":[f["id"] for f in payload["fields"]],
                "quote_refs":[{"passage_id":pid,"span_id":"q1"}]}],"unsupported":[]}
        report=review(self.item,self.sources,reviewer,batch_size=6)
        self.assertEqual(report["status"],"pass")
        self.assertEqual(len(report["checked_fields"]),len(fields_for(self.item)))
        self.assertGreater(len(calls),1)
        self.assertFalse(report["can_publish"])

    def setUp(self):
        self.item = {"evidence":[{"passage_id":"p1"}],
                     "concept_card":{k:"Classification statement" for k in ("mechanism","relevance","misconception","counterfactual")},
                     "rationale":{**{k:"Classification statement" for k in ("core_concept","why_key_wins","trap")},
                                  "distractor_breakdown":{"A":"Classification statement"}}}
        self.sources = [{"passage_id":"p1","excerpt":"Triggering agents.\nVolatile anesthetics."}]
        self.ids = [f["id"] for f in fields_for(self.item)]
        self.response = {"supported_groups":[{"field_ids":self.ids,
                         "quote_refs":[{"passage_id":"p1","span_id":"q1"}]}],"unsupported":[]}

    def test_assertion_and_false_belief_polarities_are_explicit(self):
        fields={f["label"]:f for f in fields_for(self.item)}
        self.assertEqual(fields["concept_card.mechanism"]["assessment"],"clinical_fact")
        self.assertEqual(fields["concept_card.misconception"]["assessment"],"misconception_to_refute")
        self.assertEqual(fields["concept_card.relevance"]["assessment"],"teaching_application")
        self.assertEqual(fields["rationale.distractor_breakdown.A"]["assessment"],"clinical_fact")

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

    def test_bounded_batches_cover_each_field_and_cannot_swap_or_omit_fields(self):
        calls=[]
        def reviewer(payload):
            calls.append(payload)
            return {"supported_groups":[{"field_ids":[f["id"] for f in payload["fields"]],
                "quote_refs":[{"passage_id":"p1","span_id":"q1"}]}],"unsupported":[]}
        result=review(self.item,self.sources,reviewer,batch_size=3)
        self.assertEqual(result["status"],"pass")
        self.assertEqual(result["batch_count"],3)
        self.assertEqual([len(p["fields"]) for p in calls],[3,3,2])
        self.assertEqual(len(result["checked_fields"]),8)
        self.assertEqual(review(self.item,self.sources,lambda p:self.response,batch_size=3)["status"],"pending")

    def test_unsupported_mechanism_targets_existing_rewrite_field(self):
        response = copy.deepcopy(self.response)
        response["supported_groups"][0]["field_ids"] = self.ids[1:]
        response["unsupported"] = [{"field_id":"e0","reason":"The classification does not establish receptor physiology."}]
        result = review(self.item, self.sources, lambda p:response)
        self.assertEqual(result["status"], "flag")
        self.assertEqual(result["issues"][0]["field"], "concept_card.mechanism")
        self.assertEqual(result["issues"][0]["rule_id"], "R-2.4")

    def test_model_cannot_approve_an_exclusive_clinical_claim_from_a_plain_list(self):
        self.item["rationale"]["core_concept"]="Volatile anesthetics are the only triggering agents."
        report=review(self.item,self.sources,lambda p:self.response)
        self.assertEqual(report["status"],"flag")
        self.assertIn("rationale.core_concept",[i["field"] for i in report["issues"]])
        self.assertNotIn("rationale.core_concept",report["source_support"][0]["fields"])

    def test_explicit_exclusive_source_support_can_pass_and_teaching_only_is_not_global(self):
        self.item["rationale"]["core_concept"]="Volatile anesthetics are the only triggering agents."
        self.item["concept_card"]["counterfactual"]="If only the nontriggering choice replaces the trigger, that exposure is removed."
        self.sources[0]["excerpt"]="Classification.\nOnly volatile anesthetics are triggering agents."
        report=review(self.item,self.sources,lambda p:self.response)
        self.assertEqual(report["status"],"pass")

    def test_causal_only_claims_cannot_pass_from_nonexclusive_source_examples(self):
        claims=("Static compliance is increased only by emphysema.",
                "The source lists static compliance decreases only for these conditions.",
                "The response occurs exclusively with this mechanism.")
        for text in claims:
            for label in ("core_concept","why_key_wins"):
                with self.subTest(text=text,label=label):
                    self.item["rationale"][label]=text
                    report=review(self.item,self.sources,lambda p:self.response)
                    self.assertEqual(report["status"],"flag")
                    self.assertIn("rationale."+label,[i["field"] for i in report["issues"]])
                    self.item["rationale"][label]="Classification statement"
        self.item["rationale"]["core_concept"]="Static compliance is increased by emphysema."
        self.assertEqual(review(self.item,self.sources,lambda p:self.response)["status"],"pass")

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
            response = copy.deepcopy(self.response)
            response["supported_groups"][0]["quote_refs"][0]["passage_id"] = "s0"
            return {"choices":[{"message":{"content":json.dumps(response)}}]}
        adapter=make_adapter(endpoint="https://provider.example/v1",api_key="test",model="reviewer",
                             transport=transport,owner_opt_in=True)
        packet,_=prepare({"source_passages":self.sources})
        request={"step":"explanation_review","rules_version":"2.0","auto_publish":False,
                 "independent":True,"fields":[{**f,"passage_ids":["p1"]} for f in fields_for(self.item)],"source_passages":packet["source_passages"]}
        for extra in ({"key":["A"]},{"can_publish":True},{"independent":False}):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                adapter({**request,**extra})
        self.assertEqual(calls,[])
        result = adapter(request)
        self.assertEqual(result["supported_groups"][0]["quote_refs"][0]["passage_id"], "p1")
        sent = json.loads(calls[0]["body"]["messages"][1]["content"])
        self.assertEqual(sent["source_passages"][0]["passage_id"], "s0")
        self.assertTrue(all(f["passage_ids"] == ["s0"] for f in sent["fields"]))
        self.assertEqual(request["source_passages"][0]["passage_id"], "p1")
        self.assertEqual(calls[0]["body"]["max_tokens"],1000)
        self.assertNotIn("key",json.loads(calls[0]["body"]["messages"][1]["content"]))

    def test_foreign_or_original_passage_ids_cannot_bypass_request_aliases(self):
        import json
        from item_ai_provider_v2 import make_adapter
        from item_source_quote_spans_v2 import prepare
        packet, _ = prepare({"source_passages": self.sources})
        request = {"step":"explanation_review", "rules_version":"2.0", "auto_publish":False,
                   "independent":True, "fields":[{**f,"passage_ids":["p1"]} for f in fields_for(self.item)],
                   "source_passages":packet["source_passages"]}
        for foreign in ("s1", "p1"):
            response = copy.deepcopy(self.response)
            response["supported_groups"][0]["quote_refs"][0]["passage_id"] = foreign
            adapter = make_adapter(endpoint="https://provider.example/v1", api_key="test", model="reviewer",
                transport=lambda **kw:{"choices":[{"message":{"content":json.dumps(response)}}]}, owner_opt_in=True)
            with self.subTest(foreign=foreign), self.assertRaises(ValueError):
                adapter(request)

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
        blind_issue={"rule_id":"R-12.4","message":"Two defensible answers"}
        intake.side_effect=[{"draft_reviews":[{"status":"draft","screening":{"stages":{"blind_model":{"status":"flag","issues":[blind_issue]}}}}]},
                            {"draft_reviews":[{"status":"draft","screening":{"stages":{}}}]}]
        calls = []
        def explanation(item):
            calls.append(item)
            return {**base,"status":"pass" if item.get("fixed") else "flag",
                    "issues":[] if item.get("fixed") else [issue]}
        result = generate_and_screen(lambda r:{}, mode="NCE",domain="III",section="H",objective="III.H.4",
            item_id="new-1", evidence=[{"passage_id":"p1","textbook_id":"t1","excerpt":"Source","pdf_page_start":1}],
            review_repair=lambda r:{}, explanation_review=explanation)
        self.assertEqual(len(calls), 2)
        repair.assert_called_once()
        self.assertEqual(repair.call_args.args[1], [blind_issue,issue])
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
            review_repair=lambda r:{}, explanation_review=unavailable)
        repair.assert_not_called()
        self.assertIn("explanation_evidence",result["screening"]["pending_verifications"])
        self.assertFalse(result["can_publish"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.attempt_once")
    @patch("item_generation_screened_v2.generate_one")
    def test_second_unsupported_result_stays_flagged_after_one_attempt(self, generate, repair, intake):
        intake.return_value={"draft_reviews":[{"status":"draft","screening":{"stages":{}}}]}
        generate.return_value={"item":{"item_id":"new-1"},"schema_issues":[]}
        repair.return_value={"item":{"item_id":"new-1"},"issues":[],"rewrite_attempts":1}
        issue={"rule_id":"R-2.4","message":"Unsupported claim"}
        result=generate_and_screen(lambda r:{},mode="NCE",domain="III",section="H",objective="III.H.4",
            item_id="new-1",evidence=[{"passage_id":"p1","textbook_id":"t1","excerpt":"Source","pdf_page_start":1}],
            review_repair=lambda r:{},explanation_review=lambda i:{"status":"flag","issues":[issue],"can_publish":False,
                "clinical_truth_verified":False,"human_review_required":True})
        repair.assert_called_once()
        self.assertEqual(result["screening"]["stages"]["explanation_evidence"]["status"],"flag")
        self.assertEqual(result["rewrite_attempts_used"],1)
        self.assertFalse(result["can_publish"])
