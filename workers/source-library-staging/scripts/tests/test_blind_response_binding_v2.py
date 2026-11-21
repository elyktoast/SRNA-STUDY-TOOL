import json
import unittest
from item_ai_provider_v2 import _bind_blind_response
from item_blind_review_scoring import compare
from item_ai_provider_v2 import make_adapter

class BlindResponseBindingTests(unittest.TestCase):
    def setUp(self):
        self.request={'item_id':'trusted-id','format':'MC','stem':'Which?', 'options':[{'id':'A','text':'One'},{'id':'B','text':'Two'}]}
    def test_missing_echo_is_bound_but_wrong_answer_still_fails(self):
        result=_bind_blind_response(self.request,{'key':['B']})
        self.assertEqual(result,{'item_id':'trusted-id','key':['B']})
        issues=compare({**self.request,'key':['A']},result)
        self.assertEqual(issues,[{'rule_id':'R-12.1','message':'Blind selection disagrees','expected_key':['A'],'independent_key':['B']}])
        self.assertEqual(compare({**self.request,'key':['B']},result),[])
    def test_wrong_explicit_id_and_invalid_choices_are_never_normalized(self):
        for response in ({'item_id':'other-question','key':['A']},{'key':'A'},{'key':['A','A']},{'key':['C']},{}):
            with self.subTest(response=response),self.assertRaises(ValueError):
                _bind_blind_response(self.request,response)
    def test_model_receives_neither_server_id_nor_expected_answer(self):
        calls=[]
        def transport(**kwargs):
            calls.append(kwargs);return {'choices':[{'message':{'content':'{"key":["A"]}'}}]}
        adapter=make_adapter(endpoint='https://provider.example/v1/chat/completions',api_key='test-secret',model='reviewer',transport=transport,owner_opt_in=True)
        payload={**self.request,'step':'blind_review','rules_version':'2.0','auto_publish':False,'blind':True}
        response=adapter(payload)
        model_request=json.loads(calls[0]['body']['messages'][1]['content'])
        self.assertNotIn('item_id',model_request);self.assertNotIn('key',model_request);self.assertNotIn('rationale',model_request)
        self.assertEqual(payload['item_id'],'trusted-id')
        self.assertEqual(_bind_blind_response(self.request,response),{'item_id':'trusted-id','key':['A']})
    def test_disagreement_diagnostics_preserve_multiple_answers_but_never_untrusted_text(self):
        item={**self.request,'key':['A']}
        for chosen in ([],['B'],['A','B']):
            result=compare(item,{'item_id':'trusted-id','key':chosen})
            self.assertEqual(result[0]['expected_key'],['A'])
            self.assertEqual(result[0]['independent_key'],chosen)
            self.assertEqual(result[0]['rule_id'],'R-12.1')
        for chosen in (['A','A'],['C'],['private text'],'B',None):
            result=compare(item,{'item_id':'trusted-id','key':chosen})
            self.assertNotIn('independent_key',result[0])
            self.assertNotIn('private text',json.dumps(result))
        self.assertNotIn('independent_key',compare(item,{'item_id':'other','key':['B']})[0])
        self.assertNotIn('independent_key',compare({**item,'format':'MS'},{'item_id':'trusted-id','key':['B']})[0])

    def test_other_formats_keep_typed_answer_and_trusted_identity(self):
        for kind,field,value in [('SA','numeric_answer',3.5),('DD','pairs',{'L1':'R2'}),('HS','region','top')]:
            with self.subTest(kind=kind):
                self.assertEqual(_bind_blind_response({'item_id':'q1','format':kind},{field:value}),{'item_id':'q1',field:value})

if __name__=='__main__':unittest.main()
