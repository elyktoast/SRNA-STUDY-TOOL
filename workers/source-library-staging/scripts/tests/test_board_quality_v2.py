import copy
import json
import unittest
from unittest.mock import patch
from item_board_quality_v2 import classification, obsolete_issues, editorial, options_only, stamp_checks, CRITERIA, teaching_specificity_issues
from item_ai_provider_v2 import make_adapter
from item_generation_screened_v2 import generate_and_screen


def item():
    return {"format":"MC", "domain":"III", "section":"H", "objective":"III.H.4",
        "stem":"Which intervention resolves this finding?", "reasoning_level":"application",
        "options":[{"id":x,"text":"Choice "+x,"error_pattern":"misinterprets finding"} for x in "ABCD"],
        "key":["B"], "concept_card":{"misconception":"A possible mistaken interpretation.",
        "counterfactual":"Changing the finding changes the indicated intervention."},
        "rationale":{"trap":"Choice A reflects a reversed interpretation."}, "audit":[]}


class BoardQualityTests(unittest.TestCase):
    def test_official_labels_and_unknown_objective_rejection(self):
        self.assertEqual(classification("III","H","III.H.4")["objective_label"], "Difficult airway management")
        self.assertEqual(classification("IV","B","IV.B.4")["objective_label"], "Obesity")
        self.assertEqual(classification("I","B","I.B.4")["objective_label"], "Musculoskeletal")
        for domain, section, objective in [("I","H","III.H.4"),("III","H","III.H.99"),("III","X","III.X.1")]:
            with self.subTest(objective=objective), self.assertRaises(ValueError):
                classification(domain,section,objective)

    def test_obsolete_authored_content_rejected_without_censoring_sources(self):
        q=item();q["evidence"]=[{"excerpt":"Halothane and ranitidine appear in an old source."}]
        self.assertEqual(obsolete_issues(q),[])
        for field in ("stem","rationale","concept_card"):
            bad=copy.deepcopy(q)
            if field=="stem": bad[field]="Is halothane acceptable?"
            else: bad[field]["extra"]="Use ranitidine."
            self.assertEqual(obsolete_issues(bad)[0]["rule_id"],"R-8.4")
        q["stem"]="In this explicitly historical case, halothane was used."
        self.assertEqual(obsolete_issues(q),[])

    def test_editorial_checks_have_complete_independent_coverage_and_no_key(self):
        seen=[]
        def reviewer(payload):
            seen.append(payload)
            return {"checks":{k:"flag" if k in ("counterfactual","trap") else "pass" for k in CRITERIA},
                    "findings":[{"criterion":"counterfactual","reason":"This is a restatement."},
                                {"criterion":"trap","reason":"The stated error does not lead to the distractor."}]}
        result=editorial(item(),reviewer)
        self.assertEqual(result["status"],"flag")
        self.assertEqual({i["rule_id"] for i in result["issues"]},{"R-5.3","R-9"})
        self.assertNotIn("key",seen[0]);self.assertNotIn("error_pattern",json.dumps(seen[0]))
        self.assertFalse(result["can_publish"])

    def test_missing_or_inconsistent_editorial_judgments_stay_pending(self):
        for response in ({"checks":{},"findings":[]},
                         {"checks":{k:"flag" for k in CRITERIA},"findings":[]},
                         {"checks":{k:"pass" for k in CRITERIA},"findings":[],"can_publish":True}):
            self.assertEqual(editorial(item(),lambda p:response)["status"],"pending")

    def test_options_only_trials_hide_stem_key_rationale_and_remap_shuffle(self):
        q=item();seen=[]
        def shuffle(options): options.reverse()
        def reviewer(payload):
            seen.append(payload)
            # Original B is C after reverse and fresh relabeling.
            return {"key":["C"]}
        result=options_only(q,reviewer,shuffle=shuffle)
        self.assertEqual(result["status"],"flag");self.assertEqual(result["key_guesses"],5)
        self.assertEqual(len(seen),5)
        for payload in seen:
            self.assertNotIn("stem",payload);self.assertNotIn("key",payload)
            self.assertNotIn("rationale",payload);self.assertNotIn("error_pattern",json.dumps(payload))
        self.assertEqual(q,item())

    def test_binomial_threshold_and_incomplete_trials(self):
        for guesses, expected in ((["B","B","B","B","A"],"flag"),(["B","B","B","A","A"],"pass")):
            iterator=iter(guesses)
            result=options_only(item(),lambda p:{"key":[next(iterator)]},shuffle=lambda x:None)
            self.assertEqual(result["status"],expected)
        result=options_only(item(),lambda p:{"key":["Z"]},shuffle=lambda x:None)
        self.assertEqual(result["status"],"pending");self.assertEqual(result["completed_trials"],0)

    def test_adapter_rejects_answer_or_stem_leakage_before_transport(self):
        calls=[]
        adapter=make_adapter(endpoint="https://provider.example/v1",api_key="test",model="independent",
            owner_opt_in=True,transport=lambda **kw:calls.append(kw))
        request={"step":"options_only_review","rules_version":"2.0","auto_publish":False,
                 "independent":True,"format":"MC","select_count":1,
                 "options":[{"id":x,"text":x} for x in "ABCD"]}
        for extra in ({"key":["B"]},{"stem":"Revealing question"},{"independent":False}):
            with self.subTest(extra=extra),self.assertRaises(ValueError): adapter({**request,**extra})
        self.assertEqual(calls,[])

    def test_restated_counterfactual_and_generic_trap_cannot_receive_a_pass(self):
        q=item();q["concept_card"]["counterfactual"]="The original correct answer remains appropriate."
        q["rationale"]["trap"]="A learner may select the wrong intervention."
        result=editorial(q,lambda p:{"checks":{k:"pass" for k in CRITERIA},"findings":[]})
        self.assertEqual(result["status"],"flag")
        self.assertEqual(set(result["deterministic_rules"]),{"R-5.3","R-9"})
        self.assertEqual(result["model_flagged_rules"],[])

    def test_specificity_guard_does_not_claim_semantic_verification(self):
        q=item()
        self.assertEqual(teaching_specificity_issues(q),[])
        q["rationale"]["trap"]="Option B may tempt a learner."
        self.assertIn("R-9",{i["rule_id"] for i in teaching_specificity_issues(q)})
        # A named wrong option is necessary, but the independent model must still
        # reject incoherent reasoning even when the surface form is complete.
        q["rationale"]["trap"]="Option A follows from an incoherent inference."
        response={"checks":{k:"flag" if k=="trap" else "pass" for k in CRITERIA},
                  "findings":[{"criterion":"trap","reason":"The inference leads to another choice."}]}
        self.assertEqual(editorial(q,lambda p:response)["status"],"flag")

    def test_editorial_adapter_satisfies_json_mode_provider_contract(self):
        calls=[]
        def transport(**kwargs):
            body=kwargs["body"]
            self.assertIn("json",json.dumps(body["messages"]).lower())
            self.assertEqual(body["max_tokens"],1000)
            calls.append(body)
            return {"choices":[{"message":{"content":json.dumps({"checks":{k:"pass" for k in CRITERIA},"findings":[]})}}]}
        adapter=make_adapter(endpoint="https://provider.example/v1",api_key="test",model="independent",owner_opt_in=True,transport=transport)
        result=editorial(item(),adapter)
        self.assertEqual(result["status"],"pass")
        self.assertNotIn("key",json.loads(calls[0]["messages"][1]["content"]))

    def test_server_self_check_does_not_inherit_forged_passes(self):
        q=item();q["self_check"]={"rules_checked":["EVERYTHING"],"human_approved":True}
        report={"stages":{"blind_model":{"status":"pass","issues":[]},
            "editorial_quality":{"status":"flag","issues":[{"rule_id":"R-5.3"}]},
            "duplicates":{"status":"pending","issues":[]}},
            "rewrite_original_issues":[{"rule_id":"R-5.3"}]}
        result=stamp_checks(q,report)
        self.assertEqual(result["self_check"]["blind_solve"],"pass")
        self.assertEqual(result["self_check"]["rule_results"]["R-12.9"],"pending")
        self.assertEqual(result["self_check"]["failed_then_fixed"],[])
        self.assertNotIn("EVERYTHING",result["self_check"]["rules_checked"])
        self.assertFalse(result["self_check"]["human_approved"])
        self.assertTrue(q["self_check"]["human_approved"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_generation_screened_v2.attempt_once")
    @patch("item_generation_screened_v2.generate_one")
    def test_quality_failure_uses_one_repair_and_fresh_quality_recheck(self,generate,repair,intake):
        q={"item_id":"new","format":"MC","status":"draft"}
        generate.return_value={"item":q,"schema_issues":[]}
        repair.return_value={"item":{**q,"fixed":True},"issues":[],"rewrite_attempts":1}
        intake.side_effect=lambda *a,**kw:{"draft_reviews":[{"status":"draft","screening":{"stages":{}}}]}
        calls=[]
        base={"issues":[],"can_publish":False,"human_review_required":True,"clinical_truth_verified":False}
        def quality(candidate):
            calls.append(candidate)
            return {"editorial_quality":{**base,"status":"pass" if candidate.get("fixed") else "flag",
                "issues":[] if candidate.get("fixed") else [{"rule_id":"R-5.3","message":"Restatement"}]},
                "options_only":{**base,"status":"pass"}}
        result=generate_and_screen(lambda p:{},mode="NCE",domain="III",section="H",objective="III.H.4",item_id="new",
            evidence=[{"passage_id":"p1","textbook_id":"t1","excerpt":"Source","pdf_page_start":1}],
            quality_review=quality,review_repair=lambda p:{})
        self.assertEqual(len(calls),2);repair.assert_called_once()
        self.assertEqual(result["screening"]["rewrite_attempts_used"],1)
        self.assertEqual(result["screening"]["stages"]["editorial_quality"]["status"],"pass")
        self.assertFalse(result["can_publish"])


if __name__=="__main__": unittest.main()
