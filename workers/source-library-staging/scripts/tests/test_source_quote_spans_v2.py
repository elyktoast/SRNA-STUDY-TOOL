import copy
import json
import unittest
from item_ai_provider_v2 import make_adapter
from item_source_quote_spans_v2 import prepare, hydrate


class SourceQuoteSpanTests(unittest.TestCase):
    def test_short_negations_are_preserved_as_source_context(self):
        request={"source_passages":[{"passage_id":"p1","excerpt":"No\ntriggering drugs.\nNever\nignore this warning."}]}
        packet, lookup=prepare(request)
        self.assertEqual([s["text"] for s in packet["source_passages"][0]["quote_spans"]],
                         ["No","triggering drugs.","Never","ignore this warning."])
        self.assertEqual(lookup["p1"]["q0"],"No")

    def setUp(self):
        self.request = {"step":"option_review", "rules_version":"2.0", "auto_publish":False,
            "blind":True, "format":"MC", "stem":"Which is a trigger?",
            "options":[{"id":"A","text":"Volatile agent"},{"id":"B","text":"Local anesthetic"}],
            "retrieval":{"option_audits":[{"option_id":"A","retrieved_passage_ids":["p1"]},
                                         {"option_id":"B","retrieved_passage_ids":["p2"]}]},
            "source_passages":[{"passage_id":"p1","excerpt":"Triggering (Unsafe) Agents\nSevoﬂurane is listed."},
                               {"passage_id":"p2","excerpt":"Nontriggering (Safe) Agents\nLocal anesthetics."}],
            "task":"independent_option_adjudication"}
        self.response = {"judgments":[{"option_id":"A","verdict":"refutes_distractor",
            "passage_ids":["p1"],"quote_refs":[{"passage_id":"p1","span_id":"q1"}],
            "explanation":"An intentionally wrong verdict stays wrong.","source_conflict_found":False}]}

    def test_exact_source_text_restored_without_correcting_independent_verdict(self):
        original_request, original_response = copy.deepcopy(self.request), copy.deepcopy(self.response)
        packet, lookup = prepare(self.request)
        result = hydrate(self.response, self.request, lookup)
        self.assertEqual(result["judgments"][0]["quotes"], ["Sevoﬂurane is listed."])
        self.assertEqual(result["judgments"][0]["verdict"], "refutes_distractor")
        self.assertNotIn("quote_refs", result["judgments"][0])
        self.assertNotIn("excerpt", packet["source_passages"][0])
        self.assertEqual(self.request, original_request)
        self.assertEqual(self.response, original_response)

    def test_unknown_cross_option_and_uncited_spans_rejected(self):
        _, lookup = prepare(self.request)
        for ref in [{"passage_id":"p1","span_id":"missing"},
                    {"passage_id":"unknown","span_id":"q0"},
                    {"passage_id":"p2","span_id":"q0"}]:
            response = copy.deepcopy(self.response)
            response["judgments"][0]["quote_refs"] = [ref]
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                hydrate(response, self.request, lookup)
        response = copy.deepcopy(self.response)
        response["judgments"][0]["passage_ids"] = []
        with self.assertRaises(ValueError):
            hydrate(response, self.request, lookup)

    def test_ambiguous_or_empty_quote_references_rejected(self):
        _, lookup = prepare(self.request)
        for refs in [[], None, [{"passage_id":"p1","span_id":"q0","text":"forged"}]]:
            response = copy.deepcopy(self.response)
            response["judgments"][0]["quote_refs"] = refs
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                hydrate(response, self.request, lookup)
        response = copy.deepcopy(self.response)
        response["judgments"][0]["quotes"] = ["forged"]
        with self.assertRaises(ValueError):
            hydrate(response, self.request, lookup)

    def test_uncertain_without_quotes_is_retained_as_a_blocking_judgment(self):
        from item_option_adjudication_handoff_v2 import run
        from item_option_audit_screening_v2 import attach
        from item_saved_option_review_v2 import eligible
        from test_item_draft_review_contract_v2 import passed_screening
        request = copy.deepcopy(self.request)
        response = copy.deepcopy(self.response)
        response['judgments'] = [
            {'option_id':'A','verdict':'supports_key','passage_ids':['s0'],
             'quote_refs':[{'passage_id':'s0','span_id':'q1'}],
             'explanation':'The supplied passage lists this agent.', 'source_conflict_found':False},
            {'option_id':'B','verdict':'uncertain','passage_ids':[], 'quote_refs':[],
             'explanation':'The supplied evidence does not establish this option.', 'source_conflict_found':False}]
        adapter = make_adapter(endpoint='https://provider.example/v1',api_key='test',model='reviewer',
            transport=lambda **kwargs: {'choices':[{'message':{'content':json.dumps(response)}}]},owner_opt_in=True)
        def reviewer(payload):
            result = adapter({**payload,'step':'option_review','rules_version':'2.0','auto_publish':False,'blind':True})
            return [{**j,'contradiction_found':j['source_conflict_found']} for j in result['judgments']]
        retrieval = {**request['retrieval'], 'all_options_searched':True,'all_options_have_matches':True}
        report = run({**request,'key':['A']},retrieval,reviewer,source_passages=request['source_passages'],
            generator_model_id='author',reviewer_model_id='reviewer',require_quotes=True)
        self.assertEqual(report['status'],'pending')
        self.assertNotIn('provider_rule',report)
        self.assertEqual(report['judgments'][1]['verdict'],'uncertain')
        self.assertEqual(report['judgments'][1]['quotes'],[])
        self.assertTrue(any(i.get('option_id')=='B' for i in report['issues']))
        screening = passed_screening()
        result = attach({'screening':screening},retrieval,report)
        self.assertEqual(result['screening']['stages']['independent_option_evidence']['status'],'pending')
        self.assertFalse(eligible({'format':'MC','status':'pending_review','published':False,'screening':result['screening']}))
        # Empty references never pass as source support or refutation.
        _, lookup = prepare(request)
        for verdict in ('supports_key','refutes_distractor'):
            invalid = {'judgments':[{**response['judgments'][1], 'verdict':verdict}]}
            with self.subTest(verdict=verdict), self.assertRaises(ValueError):
                hydrate(invalid,request,lookup)

    def test_failure_diagnostics_use_only_fixed_codes(self):
        from item_option_adjudication_handoff_v2 import run
        retrieval = {**self.request['retrieval'],'all_options_searched':True}
        for message, detail in [
                ('Unknown or unauthorized source quote reference','option_quote_ref_scope_invalid'),
                ('private model text and credentials','option_response_unavailable')]:
            def broken(payload):
                raise ValueError(message)
            report = run({**self.request,'key':['A']},retrieval,broken,
                source_passages=self.request['source_passages'],generator_model_id='author',reviewer_model_id='reviewer')
            self.assertEqual(report['validation_detail'],detail)
            self.assertNotIn(message,json.dumps(report))
            self.assertEqual(report['status'],'pending')
            self.assertFalse(report['can_publish'])

    def test_every_bounded_span_is_an_actual_contiguous_source_substring(self):
        self.request["source_passages"][0]["excerpt"] = "word " * 500
        packet, _ = prepare(self.request)
        for p, original in zip(packet["source_passages"], self.request["source_passages"]):
            self.assertEqual(len({s["id"] for s in p["quote_spans"]}), len(p["quote_spans"]))
            for span in p["quote_spans"]:
                self.assertTrue(1 <= len(span["text"]) <= 300)
                self.assertIn(span["text"], original["excerpt"])

    def test_option_aliases_restore_identity_without_changing_verdict_or_authorization(self):
        original=copy.deepcopy(self.request)
        response=copy.deepcopy(self.response)
        response["judgments"][0]["passage_ids"]=["s0"]
        response["judgments"][0]["quote_refs"]=[{"passage_id":"s0","span_id":"q1"}]
        def transport(**kwargs):
            sent=json.loads(kwargs["body"]["messages"][1]["content"])
            self.assertEqual([p["passage_id"] for p in sent["source_passages"]],["s0","s1"])
            self.assertEqual(sent["retrieval"]["option_audits"][0]["retrieved_passage_ids"],["s0"])
            self.assertNotIn("key",sent)
            return {"choices":[{"message":{"content":json.dumps(response)}}]}
        adapter=make_adapter(endpoint="https://provider.example/v1",api_key="secret",model="reviewer",transport=transport,owner_opt_in=True)
        result=adapter(self.request)
        self.assertEqual(self.request,original)
        self.assertEqual(result["judgments"][0]["passage_ids"],["p1"])
        self.assertEqual(result["judgments"][0]["quotes"],["Sevoﬂurane is listed."])
        self.assertEqual(result["judgments"][0]["verdict"],"refutes_distractor")
        for alias in ("s99","s1"):
            response["judgments"][0]["passage_ids"]=[alias]
            response["judgments"][0]["quote_refs"]=[{"passage_id":alias,"span_id":"q1"}]
            with self.subTest(alias=alias),self.assertRaises(ValueError):adapter(self.request)

    def test_scoped_mc_map_restores_only_identity_and_keeps_uncertain_verdict(self):
        response = {'judgments': {
            'A': {'verdict':'refutes_distractor', 'quote_refs':[{'passage_id':'s0','span_id':'q1'}],
                  'explanation':'Independent verdict remains unchanged.', 'source_conflict_found':False},
            'B': {'verdict':'uncertain', 'quote_refs':[], 'explanation':'Evidence insufficient.', 'source_conflict_found':False}}}
        sent = []
        def transport(**kwargs):
            sent.append(json.loads(kwargs['body']['messages'][1]['content']))
            return {'choices':[{'message':{'content':json.dumps(response)}}]}
        adapter = make_adapter(endpoint='https://provider.example/v1',api_key='test',model='reviewer',transport=transport,owner_opt_in=True)
        result = adapter(self.request)
        self.assertEqual([j['option_id'] for j in result['judgments']],['A','B'])
        self.assertEqual(result['judgments'][0]['passage_ids'],['p1'])
        self.assertEqual(result['judgments'][0]['quotes'],['Sevoﬂurane is listed.'])
        self.assertEqual(result['judgments'][0]['verdict'],'refutes_distractor')
        self.assertEqual(result['judgments'][1]['verdict'],'uncertain')
        self.assertEqual(result['judgments'][1]['quotes'],[])
        self.assertNotIn('key',sent[0]);self.assertNotIn('expected_verdict',str(sent[0]))
        original = copy.deepcopy(response)
        for change in ('missing','extra','forged_id','forged_citations','cross_option','wrong_span'):
            response = copy.deepcopy(original)
            a = response['judgments']['A']
            if change=='missing': del response['judgments']['B']
            if change=='extra': response['judgments']['C'] = response['judgments']['B']
            if change=='forged_id': a['option_id']='B'
            if change=='forged_citations': a['passage_ids']=['s1']
            if change=='cross_option': a['quote_refs']=[{'passage_id':'s1','span_id':'q1'}]
            if change=='wrong_span': a['quote_refs']=[{'passage_id':'s0','span_id':'unknown'}]
            with self.subTest(change=change),self.assertRaises(ValueError): adapter(self.request)

    def test_adapter_uses_bounded_span_protocol_without_answer_leakage(self):
        calls = []
        def transport(**kwargs):
            calls.append(kwargs)
            return {"choices":[{"message":{"content":json.dumps(self.response)}}]}
        adapter = make_adapter(endpoint="https://provider.example/v1/chat/completions",
            api_key="test-secret",model="reviewer",transport=transport,owner_opt_in=True)
        result = adapter(self.request)
        sent = json.loads(calls[0]["body"]["messages"][1]["content"])
        self.assertEqual(calls[0]["body"]["max_tokens"], 1000)
        self.assertIn("quote_spans", sent["source_passages"][0])
        self.assertNotIn("key", sent)
        self.assertNotIn("expected_verdict", json.dumps(sent))
        self.assertNotIn("rationale", sent)
        self.assertEqual(result["judgments"][0]["quotes"], ["Sevoﬂurane is listed."])


if __name__ == "__main__":
    unittest.main()
