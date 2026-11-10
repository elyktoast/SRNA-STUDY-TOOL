import copy
import unittest
from item_mc_choice_plan_v2 import validate, bind
from item_generation_runner_v2 import generate_one
from test_item_generation_runner_v2 import ARGS
from test_item_standard_v2 import sample


def plan():
    return {"response_variables":["Measurement X","Measurement Y"],"stem_condition":"condition X", "alternate_condition":"condition Y",
            "key":["B"],"alternate_key":["A"],"options":[
                {"id":oid,"states":states}
                for oid,states in [("A",["reduced","reduced"]),
                    ("B",["unchanged","reduced"]),
                    ("C",["unchanged","unchanged"]),
                    ("D",["reduced","unchanged"])]]}


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
        bad=copy.deepcopy(p)
        bad["options"][0]["text"]="A changed clinical response"
        with self.assertRaisesRegex(ValueError, "rendered response differs"):
            validate(bad)
        given=plan()
        given["stem_condition"]="Measurement X is reduced by condition X"
        with self.assertRaisesRegex(ValueError, "gives away a planned response"):
            validate(given)
        type_menu=plan()
        type_menu["response_variables"]=["Compliance type","Direction of change"]
        with self.assertRaisesRegex(ValueError, "not clinical components"):
            validate(type_menu)
        for change in ("stem","options","key"):
            bad=copy.deepcopy(draft)
            if change=="stem": bad["stem"]="Different case"
            if change=="options": bad["options"][0]["text"]="Unplanned alternative"
            if change=="key": bad["key"]=["A"]
            with self.subTest(change=change),self.assertRaises(ValueError):bind(p,bad)

    def test_rendering_only_formats_authored_components_and_states(self):
        raw=plan();p=validate(raw)
        self.assertEqual(p["options"][1]["text"],"Measurement X: unchanged; Measurement Y: reduced")
        self.assertNotIn("text",raw["options"][1])
        self.assertEqual(validate(p),p)
        self.assertEqual(p["key"],raw["key"])
        self.assertEqual(p["alternate_key"],raw["alternate_key"])
        self.assertEqual(p["options"][1]["states"],raw["options"][1]["states"])

    def test_repeated_variable_labels_do_not_duplicate_choice_wording_or_states(self):
        raw=plan()
        for option in raw["options"]:
            option["states"]=[f"{label}: {state}" for label,state in zip(raw["response_variables"],option["states"])]
        self.assertEqual(validate(raw),validate(plan()))
        duplicate=plan()
        duplicate["options"][2]["states"]=["Measurement X: reduced","Measurement Y: reduced"]
        with self.assertRaisesRegex(ValueError,"repeats a response pattern"):
            validate(duplicate)

    def test_plan_is_checkpointed_but_not_persisted_in_the_canonical_item(self):
        raw=plan();p=validate(raw);calls=[];checkpoints={}
        concept=dict(objective="III.H.4",mechanism="m",relevance="r",misconception="x",counterfactual="planned",evidence_ids=["p1"],choice_plan=raw)
        draft=sample();draft.update(stem="During care, condition X is observed. Which response fits?",key=["B"],
            options=[{"id":o["id"],"text":o["text"],"error_pattern":None if o["id"]=="B" else "Confuses component responses"} for o in p["options"]])
        def adapter(request):
            calls.append(request["step"])
            if request["step"]=="concept_card":return copy.deepcopy(concept)
            self.assertEqual(request["choice_plan"],p)
            self.assertNotIn("choice_plan",request["concept_card"])
            if request["step"]=="item_draft":return copy.deepcopy(draft)
            return {"core_concept":"m","why_key_wins":"r","trap":"x", "distractor_breakdown":{o["id"]:"explanation" for o in p["options"]}}
        result=generate_one(adapter,**ARGS,on_checkpoint=lambda stage,value:checkpoints.update({stage:copy.deepcopy(value)}))
        self.assertEqual(calls,["concept_card","item_draft","rationale"])
        self.assertEqual(checkpoints["concept_card"]["choice_plan"],p)
        self.assertNotIn("choice_plan",result["item"]["concept_card"])
        self.assertNotIn("choice_plan",result["item"])
        self.assertEqual(result["item"]["concept_card"]["counterfactual"],
            'If "condition X" is replaced by "condition Y", the best response changes to option(s) A.')
        self.assertFalse(result["auto_approved"])
        calls.clear()
        resumed=generate_one(adapter,**ARGS,checkpoint=checkpoints)
        self.assertEqual(calls,["rationale"])
        self.assertEqual(resumed["item"],result["item"])
        def wrapped(request):
            return {"rationale":adapter(request)}
        wrapped_result=generate_one(wrapped,**ARGS,checkpoint=checkpoints)
        self.assertEqual(wrapped_result["item"]["rationale"],result["item"]["rationale"])
        def drift(request):
            response=adapter(request)
            response["counterfactual_test"]={**bind(p,draft), "to_text":"unplanned condition"}
            return response
        with self.assertRaisesRegex(ValueError, "counterfactual differs from planned case"):
            generate_one(drift,**ARGS,checkpoint=checkpoints)
