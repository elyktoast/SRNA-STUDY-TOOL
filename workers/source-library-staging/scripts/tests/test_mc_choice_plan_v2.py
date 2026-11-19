import copy
import unittest
from item_mc_choice_plan_v2 import validate, bind, render_condition, CONDITION_SLOT, LEAD_IN_SLOT
from item_generation_runner_v2 import generate_one
from test_item_generation_runner_v2 import ARGS
from test_item_standard_v2 import sample


def plan():
    return {"response_variables":["Measurement X","Measurement Y"],"stem_condition":"condition X", "alternate_condition":"condition Y", "lead_in":"Which response fits?",
            "key":["B"],"alternate_key":["A"],
            "option_grounding":{oid:{"passage_id":"p1","span_ids":["q0"],"explanation":"Explanation for "+oid} for oid in "ABCD"},"options":[
                {"id":oid,"states":states}
                for oid,states in [("A",["reduced","reduced"]),
                    ("B",["unchanged","reduced"]),
                    ("C",["unchanged","unchanged"]),
                    ("D",["reduced","unchanged"])]]}


class ChoicePlanTests(unittest.TestCase):
    def test_option_comparison_can_cite_case_criterion_and_alternative_definition(self):
        from item_mc_choice_plan_v2 import ground_draft
        raw = plan()
        raw["option_grounding"]["A"] = {
            "source_refs": [{"passage_id": "p1", "span_ids": ["q0"]},
                            {"passage_id": "p2", "span_ids": ["q0"]}],
            "explanation": "The case measures force; the competing modality measures acceleration."}
        evidence = [{"passage_id": "p1", "excerpt": "Modality X measures contraction force."},
                    {"passage_id": "p2", "excerpt": "Modality Y measures acceleration."}]
        checked = validate(raw, evidence)
        grounded = ground_draft(checked, {})
        self.assertEqual(grounded["distractor_evidence"]["A"]["passage_ids"], ["p1", "p2"])
        self.assertEqual(grounded["distractor_evidence"]["B"]["passage_ids"], ["p1"])
        self.assertEqual(validate(checked, evidence), checked)
        for refs in ([], raw["option_grounding"]["A"]["source_refs"] * 2,
                     [{"passage_id": "p1", "span_ids": ["q0"]}] * 2,
                     [{"passage_id": "missing", "span_ids": ["q0"]}],
                     [{"passage_id": "p2", "span_ids": ["invented"]}]):
            bad = copy.deepcopy(raw)
            bad["option_grounding"]["A"]["source_refs"] = refs
            with self.assertRaises(ValueError):
                validate(bad, evidence)

    def test_ordinary_single_component_choices_remain_natural_and_bound_to_both_cases(self):
        raw=plan()
        raw['response_variables']=['Clinical response']
        raw['lead_in']='Which response is appropriate?'
        for option,state in zip(raw['options'],['Response alpha','Response beta','Response gamma','Response delta']):
            option['states']=[state]
        p=validate(raw)
        self.assertEqual([o['text'] for o in p['options']],
                         ['Response alpha','Response beta','Response gamma','Response delta'])
        self.assertEqual(validate(p),p)
        draft={'stem':CONDITION_SLOT+' Which response is appropriate?', 'key':p['key'],
               'options':[{'id':o['id'],'text':o['text']} for o in p['options']]}
        proposal=bind(p,render_condition(p,draft))
        self.assertEqual(proposal['expected_key'],['A'])
        self.assertNotEqual(proposal['expected_key'],p['key'])
        bad=copy.deepcopy(p)
        bad['options'][0]['states'].append('Unrelated second task')
        with self.assertRaises(ValueError): validate(bad)
        bad=copy.deepcopy(p)
        bad['options'][0]['states']=bad['options'][1]['states']
        bad['options'][0].pop('text')
        with self.assertRaises(ValueError): validate(bad)

    def test_standard_does_not_require_crossed_pairs_for_every_concept(self):
        from item_generation_contract_v2 import build_step
        request=build_step('concept_card',mode='NCE',domain='I',section='C',objective='I.C.5',
                           evidence=[{'passage_id':'p1','textbook_id':'t1','excerpt':'Synthetic evidence'}],format='MC')
        text=request['instructions']
        self.assertIn('ordinary homogeneous single-best-answer',text)
        self.assertIn('R-6.7',text)
        self.assertNotIn('exactly two source-supported',text)

    def test_condition_slot_preserves_exact_case_and_rejects_duplicate_cases(self):
        p=validate(plan())
        original={"stem":CONDITION_SLOT+" Which response fits?", "key":p["key"],
                  "options":[{"id":o["id"],"text":o["text"]} for o in p["options"]]}
        rendered=render_condition(p,original)
        self.assertEqual(rendered["stem"],"condition X Which response fits?")
        self.assertEqual(bind(p,rendered)["from_text"],"condition X")
        self.assertEqual(original["stem"],CONDITION_SLOT+" Which response fits?")
        for extra in (CONDITION_SLOT,p["stem_condition"],p["alternate_condition"]):
            with self.subTest(extra=extra),self.assertRaises(ValueError):
                render_condition(p,{**original,"stem":original["stem"]+extra})
        missing={**original,"stem":"A paraphrased clinical case. Which response fits?"}
        with self.assertRaises(ValueError):bind(p,render_condition(p,missing))

    def test_distinct_patterns_and_draft_binding_never_prove_clinical_correctness(self):
        p=validate(plan())
        draft={"stem":"condition X Which response fits?", "key":["B"],
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
        draft=sample();draft.pop("distractor_evidence",None);draft.update(stem="condition X Which response fits?",key=["B"],
            options=[{"id":o["id"],"text":o["text"],"error_pattern":None if o["id"]=="B" else "Confuses component responses"} for o in p["options"]])
        def adapter(request):
            calls.append(request["step"])
            if request["step"]=="concept_card":return copy.deepcopy(concept)
            self.assertEqual(request["choice_plan"],p)
            self.assertNotIn("choice_plan",request["concept_card"])
            if request["step"]=="item_draft":
                return {**copy.deepcopy(draft),"stem":draft["stem"].replace(p["stem_condition"],CONDITION_SLOT)}
            return {"core_concept":"m","why_key_wins":"r","trap":"x", "distractor_breakdown":{oid:entry["explanation"] for oid,entry in p["option_grounding"].items()}}
        result=generate_one(adapter,**ARGS,on_checkpoint=lambda stage,value:checkpoints.update({stage:copy.deepcopy(value)}))
        self.assertEqual(calls,["concept_card","item_draft","rationale"])
        self.assertEqual(checkpoints["concept_card"]["choice_plan"],p)
        self.assertNotIn("choice_plan",result["item"]["concept_card"])
        self.assertNotIn("choice_plan",result["item"])
        self.assertEqual(result["item"]["concept_card"]["counterfactual"],
            'If "condition X" is replaced by "condition Y", the best response changes to option(s) A.')
        self.assertFalse(result["auto_approved"])
        def rationale_drift(request):
            response=adapter(request)
            response['distractor_breakdown']['A']='Unsupported new alarm behavior'
            return response
        with self.assertRaisesRegex(ValueError,'option grounding differs'):
            generate_one(rationale_drift,**ARGS,checkpoint=checkpoints)
        def concise_rationale(request):
            response=adapter(request)
            response.pop('distractor_breakdown')
            return response
        carried=generate_one(concise_rationale,**ARGS,checkpoint=checkpoints)
        self.assertEqual(carried['item']['rationale'],result['item']['rationale'])
        self.assertEqual(carried['item']['distractor_evidence']['A']['explanation'],
                         carried['item']['rationale']['distractor_breakdown']['A'])
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

    def test_shared_lead_in_is_required_and_cannot_embed_either_case(self):
        for value in (None, '', 'A declarative answer', 'condition X Which response fits?'):
            raw=plan();raw['lead_in']=value
            with self.subTest(value=value),self.assertRaises(ValueError):validate(raw)
        raw=plan();raw.pop('lead_in')
        with self.assertRaises(ValueError):validate(raw)

    def test_two_slots_render_only_the_complete_authored_plan(self):
        p=validate(plan())
        original={'stem':CONDITION_SLOT+' '+LEAD_IN_SLOT,'key':p['key'],
                  'options':[{'id':o['id'],'text':o['text']} for o in p['options']]}
        rendered=render_condition(p,original)
        self.assertEqual(rendered['stem'],'condition X Which response fits?')
        self.assertEqual(bind(p,rendered)['expected_key'],['A'])
        self.assertEqual(original['stem'],CONDITION_SLOT+' '+LEAD_IN_SLOT)
        self.assertNotIn('can_publish',rendered)

    def test_later_drafting_cannot_change_the_question_or_add_unplanned_context(self):
        p=validate(plan())
        options=[{'id':o['id'],'text':o['text']} for o in p['options']]
        for stem in ('condition X Which different outcome is responsible?',
                     'During care, condition X Which response fits?',
                     CONDITION_SLOT+' Which different outcome is responsible?',
                     CONDITION_SLOT+' '+LEAD_IN_SLOT+' Additional finding.'):
            with self.subTest(stem=stem),self.assertRaises(ValueError):
                bind(p,render_condition(p,{'stem':stem,'key':p['key'],'options':options}))

    def test_grounding_rejects_missing_options_unknown_sources_and_fabricated_quotes(self):
        from item_mc_choice_plan_v2 import ground_draft, option_explanations
        evidence=[{"passage_id":"p1","excerpt":"Source with a line\nbreak."}]
        p=validate(plan(),evidence)
        p['option_grounding']['A']['span_ids']=['q1']
        self.assertEqual(validate(p,evidence),p)
        for change in ('missing','extra','unknown','fabricated','empty','too_long','approval'):
            bad=copy.deepcopy(p)
            if change=='missing':bad['option_grounding'].pop('D')
            if change=='extra':bad['option_grounding']['E']=bad['option_grounding']['A']
            if change=='unknown':bad['option_grounding']['A']['passage_id']='other'
            if change=='fabricated':bad['option_grounding']['A']['span_ids']=['invented']
            if change=='empty':bad['option_grounding']['A']['explanation']=' '
            if change=='too_long':bad['option_grounding']['A']['span_ids']=['q0']*4
            if change=='approval':bad['option_grounding']['A']['approved']=True
            with self.subTest(change=change),self.assertRaises(ValueError):validate(bad,evidence)
        original={'stem':'unchanged'}
        grounded=ground_draft(p,original)
        self.assertNotIn('distractor_evidence',original)
        self.assertEqual(grounded['distractor_evidence']['B']['verdict'],'supports_key')
        self.assertEqual(grounded['distractor_evidence']['A']['verdict'],'refutes_distractor')
        self.assertEqual(ground_draft(p,grounded),grounded)
        self.assertEqual(option_explanations(p)['A'],grounded['distractor_evidence']['A']['explanation'])
        bad=copy.deepcopy(grounded);bad['distractor_evidence']['A']['explanation']='Unsupported new alarm behavior'
        with self.assertRaisesRegex(ValueError,'grounding'):ground_draft(p,bad)

    def test_invalid_grounding_blocks_before_drafting_and_on_checkpoint_replay(self):
        raw=plan();raw['option_grounding']['D']['span_ids']=['invented']
        concept=dict(objective='III.H.4',mechanism='m',relevance='r',misconception='x',counterfactual='planned',evidence_ids=['p1'],choice_plan=raw)
        calls=[];checkpoints=[]
        def adapter(request):
            calls.append(request['step']);return copy.deepcopy(concept)
        with self.assertRaisesRegex(ValueError,'span not in source'):
            generate_one(adapter,**ARGS,on_checkpoint=lambda *args:checkpoints.append(args))
        self.assertEqual(calls,['concept_card']);self.assertEqual(checkpoints,[])
        calls.clear()
        with self.assertRaisesRegex(ValueError,'span not in source'):
            generate_one(adapter,**ARGS,checkpoint={'concept_card':concept})
        self.assertEqual(calls,[])

    def test_grounding_contract_does_not_claim_clinical_support_or_change_other_formats(self):
        from item_generation_contract_v2 import build_step
        args=dict(mode='NCE',domain='I',section='C',objective='I.C.5',evidence=[{'passage_id':'p1','textbook_id':'t1','excerpt':'Source'}])
        mc=build_step('concept_card',format='MC',**args)
        self.assertIn('option_grounding',mc['instructions'])
        self.assertIn('same level of specificity to EVERY option',mc['instructions'])
        self.assertFalse(mc['auto_publish'])
        other=build_step('concept_card',format='MS',**args)
        self.assertNotIn('option_grounding',other['instructions'])
