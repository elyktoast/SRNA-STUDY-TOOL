import unittest
from unittest.mock import patch
from item_option_retrieval_audit_v2 import audit

class MeasurementRetrievalTests(unittest.TestCase):
    def test_definition_candidates_precede_name_lists_without_authorizing_any_answer(self):
        calls=[]
        item={'format':'MC','stem':'Which measurement?',
              'options':[{'id':'A','text':'Astergraphy'}],'key':['A']}
        def search(conn,query,owner,*,limit,textbook_id):
            calls.append((query,owner,textbook_id,limit))
            if ' records OR ' in query:
                return [{'passage_id':'definition','excerpt':'Astergraphy measures a fictional force.'}] if textbook_id=='00000000-0000-4000-8000-000000000002' else []
            return [{'passage_id':'names-'+textbook_id,'excerpt':'Astergraphy, Birchgraphy, Cedargraphy'}]
        with patch('item_option_retrieval_audit_v2.search',side_effect=search):
            result=audit(None,'owner',item,textbook_id='00000000-0000-4000-8000-000000000001',textbook_ids=['00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002'],limit=2)
        self.assertEqual(result['option_audits'][0]['retrieved_passage_ids'][0],'definition')
        self.assertLessEqual(result['option_audits'][0]['retrieved_count'],2)
        self.assertTrue(all(c[1]=='owner' and c[2] in ('00000000-0000-4000-8000-000000000001','00000000-0000-4000-8000-000000000002') and c[3]==2 for c in calls))
        self.assertFalse(result['clinical_verification_complete'])
        self.assertFalse(result['can_publish'])

    def test_empty_context_does_not_waste_the_reserved_passage_budget(self):
        item={'format':'MC','stem':'Which?', 'options':[{'id':'A','text':'ordinary option'}],'key':['A']}
        calls=[]
        def search(conn,query,owner,*,limit,textbook_id):
            calls.append((query,limit))
            return [] if query=='missing context' else [{'passage_id':str(i)} for i in range(limit)]
        with patch('item_option_retrieval_audit_v2.search',side_effect=search):
            result=audit(None,'owner',item,textbook_id='book',limit=4,context_query='missing context')
        self.assertEqual(calls,[('missing context',2),('ordinary option',4)])
        self.assertEqual(result['option_audits'][0]['retrieved_count'],4)

    def test_definition_lookup_falls_back_to_the_label_without_claiming_proof(self):
        item={'format':'MC','stem':'Which?', 'options':[{'id':'A','text':'Birchmetry'}],'key':['A']}
        with patch('item_option_retrieval_audit_v2.search',side_effect=lambda conn,q,owner,**kw:
                   [{'passage_id':'ordinary'}] if q=='Birchmetry' else []):
            result=audit(None,'owner',item,textbook_id='book',limit=2)
        self.assertEqual(result['option_audits'][0]['retrieved_passage_ids'],['ordinary'])
        self.assertEqual(result['option_audits'][0]['independent_verification'],'pending')
