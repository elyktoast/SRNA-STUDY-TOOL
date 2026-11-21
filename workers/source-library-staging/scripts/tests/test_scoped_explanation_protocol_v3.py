import json
import unittest
from copy import deepcopy
from unittest.mock import patch
from item_ai_provider_v2 import make_adapter
from item_grounded_pipeline_v2 import generate_from_index


class ScopedExplanationTests(unittest.TestCase):
    def request(self):
        return {'step':'explanation_review','rules_version':'2.0','auto_publish':False,'independent':True,
            'fields':[{'id':'e0','label':'concept_card.mechanism','text':'A source fact',
                       'assessment':'clinical_fact','passage_ids':['one']},
                      {'id':'e1','label':'concept_card.relevance','text':'A teaching distinction',
                       'assessment':'teaching_application','passage_ids':['two']}],
            'source_passages':[{'passage_id':pid,'quote_spans':[{'id':'q1','text':'Positive source statement.'}]}
                               for pid in ('one','two')]}

    def adapter(self,response):
        return make_adapter(endpoint='https://api.groq.com/openai/v1/chat/completions',
            api_key='fixture',model='reviewer',owner_opt_in=True,staging=True,
            transport=lambda **kw:{'choices':[{'message':{'content':json.dumps(response)}}]})

    def test_definite_support_requires_own_exact_source_span(self):
        response={'judgments':{'e0':{'supported':True,'quote_refs':['s0:q1'],'reason':''},
                               'e1':{'supported':None,'quote_refs':None,'reason':'Insufficient evidence'}}}
        result=self.adapter(response)(self.request())
        self.assertEqual(result['supported_groups'],[{'field_ids':['e0'],
            'quote_refs':[{'passage_id':'one','span_id':'q1'}]}])
        self.assertEqual(result['unsupported'],[{'field_id':'e1','reason':'Insufficient evidence'}])
        for refs in (None, [], ['s1:q1'], ['s0:invented'], ['one:q1']):
            broken=deepcopy(response);broken['judgments']['e0']['quote_refs']=refs
            with self.subTest(refs=refs),self.assertRaises(ValueError):
                self.adapter(broken)(self.request())
        del response['judgments']['e1']
        with self.assertRaises(ValueError): self.adapter(response)(self.request())

    def test_pending_or_flagged_source_review_never_invokes_paid_option_review(self):
        source={'passage_id':'p1','textbook_id':'book','excerpt':'Indexed source',
                'pdf_page_start':1,'pdf_page_end':1,'citation_verified':False}
        packet={'topic':'topic','can_generate_grounded_questions':True,'sources':[source]}
        item={'format':'MC','stem':'A stem','key':['A'],'options':[{'id':x,'text':x} for x in 'ABCD']}
        audit={'all_options_searched':True,'all_options_have_matches':True,'option_audits':[]}
        for status, blind_status in (('pending','pass'),('flag','pass'),('pass','pass'),('pass','pending')):
            report={'item':deepcopy(item),'generator_issues':[],'screening':{'stages':{
                'schema':{'status':'pass'},'explanation_evidence':{'status':status,'issues':[]},
                'blind_model':{'status':blind_status},'human_review':{'status':'pending'}}}}
            with patch('item_grounded_pipeline_v2.generate_and_screen',return_value=report), \
                 patch('item_option_retrieval_audit_v2.audit',return_value=audit), \
                 patch('item_option_adjudication_handoff_v2.run',return_value={'status':'pending','issues':[]}) as review:
                generate_from_index(object(),'owner','topic',lambda _:None,mode='NCE',domain='II',
                    section='C',objective='II.C.4',item_id='new',textbook_id='book',evidence_packet=packet,
                    generator_model_id='author',option_reviewer_model_id='reviewer',
                    option_reviewer=lambda _:None,explanation_review=lambda _:None)
            self.assertEqual(review.call_count,1 if status=='pass' and blind_status=='pass' else 0)
