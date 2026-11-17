import unittest
from unittest.mock import patch
from item_option_retrieval_audit_v2 import audit


class OptionContextEvidenceTests(unittest.TestCase):
    def test_unmatched_paired_options_retain_both_context_components(self):
        item = {'format':'MC','stem':'Which paired response follows this event?',
                'options':[{'id':oid,'text':text} for oid,text in
                           [('A','X low; Y unchanged'),('B','X unchanged; Y low')]],'key':['B']}
        calls=[]
        def search(conn, query, owner, *, limit, textbook_id):
            calls.append((query,limit))
            return [{'passage_id':'component-x'},{'passage_id':'component-y'}][:limit] if query=='paired concept' else []
        with patch('item_option_retrieval_audit_v2.search',side_effect=search):
            report=audit(None,'owner',item,textbook_id='book',limit=2,context_query='paired concept')
        for option in report['option_audits']:
            self.assertEqual(option['retrieved_passage_ids'],['component-x','component-y'])
            self.assertEqual(option['retrieved_count'],2)
            self.assertEqual(option['independent_verification'],'pending')
        self.assertEqual(len(calls),3)
        self.assertFalse(report['clinical_verification_complete'])
        self.assertFalse(report['can_publish'])

    def test_direct_option_evidence_keeps_priority_without_exceeding_budget(self):
        item={'format':'MC','stem':'Which response?', 'options':[{'id':'A','text':'specific option'}],'key':['A']}
        def search(conn, query, owner, *, limit, textbook_id):
            return ([{'passage_id':'context-1'},{'passage_id':'context-2'}] if query=='context'
                    else [{'passage_id':'direct'}])[:limit]
        with patch('item_option_retrieval_audit_v2.search',side_effect=search):
            report=audit(None,'owner',item,textbook_id='book',limit=2,context_query='context')
        self.assertEqual(report['option_audits'][0]['retrieved_passage_ids'],['direct','context-1'])

    def test_three_passage_budget_keeps_direct_match_and_both_context_components(self):
        item={'format':'MC','stem':'Which pair?', 'options':[{'id':'A','text':'specific pair'}],'key':['A']}
        calls=[]
        def search(conn,query,owner,*,limit,textbook_id):
            calls.append((query,limit))
            return ([{'passage_id':'context-x'},{'passage_id':'context-y'}] if query=='context'
                    else [{'passage_id':'direct'}])[:limit]
        with patch('item_option_retrieval_audit_v2.search',side_effect=search):
            report=audit(None,'owner',item,textbook_id='book',limit=3,context_query='context')
        self.assertEqual(calls,[('context',2),('specific pair',1)])
        self.assertEqual(report['option_audits'][0]['retrieved_passage_ids'],['direct','context-x','context-y'])
        self.assertFalse(report['clinical_verification_complete'])

    def test_mc_lecture_context_uses_same_clinical_query_as_evidence_preflight(self):
        topic='Explain the relationship between functional residual capacity and oxygen reserve during apnea.'
        clinical='functional residual capacity and oxygen reserve during apnea.'
        item={'format':'MC','stem':'Which response?', 'options':[{'id':'A','text':'decreased oxygen reserve'}],'key':['A']}
        calls=[]
        def search(conn,query,owner,*,limit,textbook_id):
            calls.append((query,owner,textbook_id,limit))
            return [{'passage_id':'independently-found'}] if query==clinical else []
        with patch('item_option_retrieval_audit_v2.search',side_effect=search):
            report=audit(None,'owner',item,textbook_id='book',limit=3,context_query=topic)
        self.assertEqual(calls,[(clinical,'owner','book',2),('decreased oxygen reserve','owner','book',1)])
        self.assertTrue(report['all_options_have_matches'])
        self.assertEqual(report['option_audits'][0]['search_queries'],['decreased oxygen reserve',clinical])
        self.assertFalse(report['clinical_verification_complete'])
        self.assertFalse(report['can_publish'])

    def test_normalized_mc_context_with_no_passages_stays_incomplete(self):
        item={'format':'MC','stem':'Which response?', 'options':[{'id':'A','text':'unsupported response'}],'key':['A']}
        with patch('item_option_retrieval_audit_v2.search',return_value=[]):
            report=audit(None,'owner',item,textbook_id='book',limit=3,context_query='Explain oxygen reserve')
        self.assertFalse(report['all_options_have_matches'])
        self.assertFalse(report['clinical_verification_complete'])

    def test_mc_context_normalization_does_not_change_ms_contract(self):
        item={'format':'MS','stem':'Which responses?', 'options':[{'id':'A','text':'response'}],'key':['A']}
        with patch('item_option_retrieval_audit_v2.search',return_value=[]) as search:
            audit(None,'owner',item,textbook_id='book',limit=3,context_query='Explain oxygen reserve')
        self.assertEqual(search.call_args_list[0].args[1],'Explain oxygen reserve')
