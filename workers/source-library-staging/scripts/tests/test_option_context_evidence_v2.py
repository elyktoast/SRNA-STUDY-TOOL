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
