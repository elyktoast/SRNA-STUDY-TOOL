import copy
import unittest
from item_mc_choice_plan_v2 import validate, bind
from item_generation_runner_v2 import generate_one
from test_item_generation_runner_v2 import ARGS
from test_item_standard_v2 import sample


def plan():
    return {"dimensions":["component X","component Y"],"stem_condition":"condition X", "alternate_condition":"condition Y",
            "key":["B"],"alternate_key":["A"],"options":[
                {"id":oid,"text":text,"states":states}
                for oid,text,states in [("A","X reduced; Y reduced",["reduced","reduced"]),
                    ("B","X unchanged; Y reduced",["unchanged","reduced"]),
                    ("C","X unchanged; Y unchanged",["unchanged","unchanged"]),
                    ("D","X reduced; Y unchanged",["reduced","unchanged"])]]}


class ChoicePlanTests(unittest.TestCase):
    def test_distinct_patterns_and_draft_binding_never_prove_clinical_correctness(self):
        p=validate(plan())
        draft={"stem":"During care, condition X is observed. Which response fits?", "key":["B"],
               "options":[{"id":o["id"],"text":o["text"],"error_pattern":None if o["id"]=="B" else "Confuses component responses"} for o in p["options"]]}
        proposal=bind(p,draft)
        self.assertEqual(proposal,{"from_text":"condition X","to_text":"condition Y","expected_key":["A"]})
        for change in ("duplicate_pattern","same_key","same_condition","bad_order","missing_state"):
            bad=copy.deepcopy(p)
            if change=="duplicate_pattern": bad["options"][2]["states"]=bad["options"][0]["states"]
            if change=="same_key": bad["alternate_key"]=["B"]
            if change=="same_condition": bad["alternate_condition"]="condition X"
            if change=="bad_order": bad["options"].reverse()
            if change=="missing_state": bad["options"][0]["states"].pop()
            with self.subTest(change=change),self.assertRaises(ValueError):validate(bad)
        for change in ("stem","options","key"):
            bad=copy.deepcopy(draft)
            if change=="stem": bad["stem"]="Different case"
            if change=="options": bad["options"][0]["text"]="Unplanned alternative"
            if change=="key": bad["key"]=["A"]
            with self.subTest(change=change),self.assertRaises(ValueError):bind(p,bad)

    def test_plan_is_checkpointed_but_not_persisted_in_the_canonical_item(self):
        p=plan();calls=[];checkpoints={}
        concept=dict(objective="III.H.4",mechanism="m",relevance="r",misconception="x",counterfactual="planned",evidence_ids=["p1"],choice_plan=p)
        draft=sample();draft.update(stem="During care, condition X is observed. Which response fits?",key=["B"],
            options=[{"id":o["id"],"text":o["text"],"error_pattern":None if o["id"]=="B" else "Confuses component responses"} for o in p["options"]])
        def adapter(request):
            calls.append(request["step"])
            if request["step"]=="concept_card":return copy.deepcopy(concept)
            self.assertEqual(request["choice_plan"],p)
            self.assertNotIn("choice_plan",request["concept_card"])
            if request["step"]=="item_draft":return copy.deepcopy(draft)
            return {"core_concept":"m","why_key_wins":"r","trap":"x", "distractor_breakdown":{o["id"]:"explanation" for o in p["options"]},
                    "counterfactual_test":bind(p,draft)}
        result=generate_one(adapter,**ARGS,on_checkpoint=lambda stage,value:checkpoints.update({stage:copy.deepcopy(value)}))
        self.assertEqual(calls,["concept_card","item_draft","rationale"])
        self.assertEqual(checkpoints["concept_card"]["choice_plan"],p)
        self.assertNotIn("choice_plan",result["item"]["concept_card"])
        self.assertNotIn("choice_plan",result["item"])
        self.assertFalse(result["auto_approved"])
        calls.clear()
        resumed=generate_one(adapter,**ARGS,checkpoint=checkpoints)
        self.assertEqual(calls,["rationale"])
        self.assertEqual(resumed["item"],result["item"])

