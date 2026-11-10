import copy
import json
import unittest
from unittest.mock import patch
from item_ai_provider_v2 import make_adapter
from item_option_adjudication_handoff_v2 import run
from item_option_audit_screening_v2 import attach

class LiveOptionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.item = {'format':'MC','stem':'Which is a trigger?', 'options':[{'id':'A','text':'Volatile agent'},{'id':'B','text':'Local anesthetic'}], 'key':['A']}
        self.sources = [{'passage_id':'p1','excerpt':'Volatile agents are triggering. Local anesthetics are nontriggering.'}]
        self.audit = {'all_options_searched':True,'all_options_have_matches':True,'option_audits':[{'option_id':i,'retrieved_passage_ids':['p1'],'search_status':'matches_found','search_query':'clinical query'} for i in ('A','B')]}
        self.judgments = [{'option_id':i,'passage_ids':['p1'],'verdict':v,'explanation':'The cited classification establishes this choice.', 'quotes':[q],'contradiction_found':False} for i,v,q in [('A','supports_key','Volatile agents are triggering.'),('B','refutes_distractor','Local anesthetics are nontriggering.')]]
    def review(self, judgments=None, audit=None):
        captured=[]
        def reviewer(request):
            captured.append(request)
            return self.judgments if judgments is None else judgments
        report=run(self.item, self.audit if audit is None else audit, reviewer,
                   source_passages=self.sources,generator_model_id='generator',reviewer_model_id='reviewer',require_quotes=True)
        return report,captured
    def test_blind_source_review_passes_with_verbatim_quotes_but_never_approves(self):
        report,captured=self.review()
        self.assertEqual(report['status'],'reviewed')
        self.assertNotIn('key', captured[0]); self.assertNotIn('rationale', captured[0])
        self.assertNotIn('expected_verdict', str(captured[0]))
        result=attach({'screening':{'stages':{'human_review':{'status':'pending'}},'pending_verifications':['duplicates','independent_option_evidence']}},self.audit,report)
        self.assertEqual(result['screening']['stages']['independent_option_evidence']['status'],'pass')
        self.assertEqual(result['screening']['pending_verifications'],['duplicates'])
        self.assertEqual(result['screening']['stages']['human_review']['status'],'pending')
        self.assertFalse(result['can_publish']); self.assertFalse(report['clinical_truth_verified'])
        self.assertEqual(result['screening']['independent_option_adjudication']['judgments'],self.judgments)
    def test_paired_key_needs_both_components_but_refutation_can_use_one(self):
        self.item={'format':'MC','stem':'Which pair follows the event?',
                   'options':[{'id':'A','text':'Component X: unchanged; Component Y: decreased'},
                              {'id':'B','text':'Component X: decreased; Component Y: decreased'}], 'key':['A']}
        self.sources=[{'passage_id':'p1','excerpt':'Component X remains unchanged.'},
                      {'passage_id':'p2','excerpt':'Component Y is decreased.'}]
        for audit in self.audit['option_audits']:
            audit['retrieved_passage_ids']=['p1','p2']
        self.judgments=[{'option_id':oid,'passage_ids':['p1'],'verdict':verdict,
                        'explanation':'X is unchanged.', 'quotes':['Component X remains unchanged.'],
                        'contradiction_found':False} for oid,verdict in [('A','supports_key'),('B','refutes_distractor')]]
        report,_=self.review()
        self.assertEqual(report['status'],'pending')
        self.assertEqual([i['option_id'] for i in report['issues']],['A'])
        self.assertIn('paired response component',report['issues'][0]['message'])
        self.judgments[0]['passage_ids'].append('p2')
        self.judgments[0]['quotes'].append('Component Y is decreased.')
        report,_=self.review()
        self.assertEqual(report['status'],'reviewed')
        # Full support can also occur in ONE passage; no arbitrary two-source rule.
        self.sources[0]['excerpt']+=' Component Y is decreased.'
        self.judgments[0]['passage_ids']=['p1']
        report,_=self.review()
        self.assertEqual(report['status'],'reviewed')
        self.assertFalse(report['clinical_truth_verified'])
        self.assertFalse(report['can_publish'])

    def test_fabricated_quote_or_wrong_citation_never_clears_gate(self):
        for field,value in [('quotes',['Fabricated source quotation']),('passage_ids',['unknown']),('contradiction_found',True),('verdict','supports_key')]:
            with self.subTest(field=field):
                judgments=copy.deepcopy(self.judgments); judgments[1][field]=value
                report,_=self.review(judgments)
                self.assertEqual(report['status'],'pending')
                result=attach({'screening':{'stages':{}}},self.audit,report)
                self.assertEqual(result['screening']['stages']['independent_option_evidence']['status'],'pending')
    def test_separate_table_fragments_are_checked_without_synthesizing_a_quote(self):
        self.sources[0]['excerpt']='Triggering (Unsafe) Agents. Unrelated column text. Volatile agents. Nontriggering (Safe) Agents. More column text. Local anesthetics.'
        judgments=copy.deepcopy(self.judgments)
        judgments[0]['quotes']=['Triggering (Unsafe) Agents','Volatile agents']
        judgments[1]['quotes']=['Nontriggering (Safe) Agents','Local anesthetics']
        report,_=self.review(judgments)
        self.assertEqual(report['status'],'reviewed')
        judgments[0]['quotes']=['Triggering (Unsafe) Agents Volatile agents']
        report,_=self.review(judgments)
        self.assertEqual(report['status'],'pending')

    def test_source_silence_is_not_refutation(self):
        judgments=copy.deepcopy(self.judgments); judgments[1]['explanation']='The source does not mention this option.'
        report,_=self.review(judgments); self.assertEqual(report['status'],'pending')
    def test_missing_retrieval_blocks_paid_reviewer(self):
        report,captured=self.review(audit={**self.audit,'all_options_have_matches':False})
        self.assertEqual(captured,[]); self.assertEqual(report['status'],'pending')
    def test_no_fabricated_review_status_from_same_model(self):
        report,_=self.review(); report['reviewer_model_id']='generator'
        result=attach({'screening':{'stages':{}}},self.audit,report)
        self.assertEqual(result['screening']['stages']['independent_option_evidence']['status'],'pending')
    def test_adapter_rejects_answer_bearing_option_review_before_transport(self):
        calls=[]
        adapter=make_adapter(endpoint='https://provider.example/v1/chat/completions',api_key='test-secret',model='reviewer',transport=lambda **kw:calls.append(kw),owner_opt_in=True)
        _,captured=self.review()
        payload={**captured[0],'step':'option_review','blind':True,'rules_version':'2.0','auto_publish':False}
        for extra in ({'key':['A']},{'rationale':'revealed'},{'options':[{'id':'A','text':'One','is_correct':True}]},{'retrieval':{'option_audits':[{'option_id':'A','retrieved_passage_ids':['p1'],'expected_verdict':'supports_key'}]}}):
            with self.subTest(extra=extra):
                with self.assertRaises(ValueError): adapter({**payload,**extra})
        self.assertEqual(calls,[])
    @patch('item_option_retrieval_audit_v2.audit')
    @patch('item_grounded_pipeline_v2.generate_and_screen')
    @patch('search_passages.search')
    def test_indexed_pipeline_persists_review_and_skips_it_for_invalid_drafts(self, search, screen, audit):
        from item_grounded_pipeline_v2 import generate_from_index
        source={**self.sources[0],'textbook_id':'book','pdf_page_start':1,'pdf_page_end':1,'citation_verified':False}
        packet={'can_generate_grounded_questions':True,'topic':'clinical topic','sources':[source]}
        screen.return_value={'item':self.item,'generator_issues':[], 'screening':{'stages':{'schema':{'status':'pass'},'human_review':{'status':'pending'}}}}
        audit.return_value=self.audit; search.return_value=[source]
        calls=[]
        def reviewer(payload): calls.append(payload); return self.judgments
        kwargs=dict(mode='NCE',domain='III',section='H',objective='III.H.4',item_id='q1',textbook_id='book',evidence_packet=packet,option_reviewer=reviewer,generator_model_id='generator',option_reviewer_model_id='reviewer')
        result=generate_from_index(object(),'owner','clinical topic',lambda r:{},**kwargs)
        self.assertEqual(len(calls),1)
        self.assertEqual(audit.call_args.kwargs['context_query'],'clinical topic')
        self.assertEqual(result['screening']['stages']['independent_option_evidence']['status'],'pass')
        self.assertFalse(result['can_publish'])
        screen.return_value={**screen.return_value,'generator_issues':[{'rule_id':'R-15'}]}
        generate_from_index(object(),'owner','clinical topic',lambda r:{},**kwargs)
        self.assertEqual(len(calls),1)

    def test_adapter_sends_distinct_review_step_with_bounded_output(self):
        calls=[]
        def transport(**kwargs):
            calls.append(kwargs); return {'choices':[{'message':{'content':json.dumps({'judgments':self.judgments})}}]}
        adapter=make_adapter(endpoint='https://provider.example/v1/chat/completions',api_key='test-secret',model='reviewer',transport=transport,owner_opt_in=True)
        _,captured=self.review()
        result=adapter({**captured[0],'step':'option_review','blind':True,'rules_version':'2.0','auto_publish':False})
        self.assertEqual(result['judgments'],self.judgments)
        self.assertEqual(calls[0]['body']['max_tokens'],1400)
        self.assertNotIn('key', json.loads(calls[0]['body']['messages'][1]['content']))

if __name__=='__main__': unittest.main()
