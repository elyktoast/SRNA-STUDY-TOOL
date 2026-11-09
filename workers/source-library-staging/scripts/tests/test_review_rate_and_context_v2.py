import unittest
from unittest.mock import Mock, patch
from run_grounded_generation_v2 import _call_with_bounded_rate_wait
from item_ai_https_transport_v2 import TransportError
from item_option_retrieval_audit_v2 import audit

class ReviewRateAndContextTests(unittest.TestCase):
    @patch('time.sleep')
    def test_only_explicit_bounded_429_can_wait_and_retry_once(self, sleep):
        request={'step':'option_review'}
        adapter=Mock(side_effect=[TransportError('PROVIDER_RATE_LIMIT',retry_after_seconds=3), {'judgments':[]}])
        self.assertEqual(_call_with_bounded_rate_wait(adapter,request),{'judgments':[]})
        sleep.assert_called_once_with(4); self.assertEqual(adapter.call_count,2)
        self.assertIs(adapter.call_args.args[0],request)
        for error in (TransportError('PROVIDER_TIMEOUT'),TransportError('PROVIDER_RATE_LIMIT'),TransportError('PROVIDER_RATE_LIMIT',retry_after_seconds=61)):
            with self.subTest(rule=error.rule):
                sleep.reset_mock(); adapter=Mock(side_effect=error)
                with self.assertRaises(TransportError): _call_with_bounded_rate_wait(adapter,request)
                sleep.assert_not_called();self.assertEqual(adapter.call_count,1)
    @patch('time.sleep')
    def test_second_429_is_not_retried(self,sleep):
        adapter=Mock(side_effect=TransportError('PROVIDER_RATE_LIMIT',retry_after_seconds=2))
        with self.assertRaises(TransportError):_call_with_bounded_rate_wait(adapter,{})
        sleep.assert_called_once_with(3);self.assertEqual(adapter.call_count,2)
    @patch('item_option_retrieval_audit_v2.search')
    def test_topic_and_classification_retrieved_once_without_answer_or_citation_seeding(self,search):
        def lookup(conn,query,owner,**kwargs):
            self.assertEqual(owner,'owner');self.assertEqual(kwargs,{'limit':1,'textbook_id':'book'})
            return [{'passage_id':'topic-source' if query=='topic' else query+'-class-source'}]
        search.side_effect=lookup
        item={'format':'MC','stem':'Which?', 'options':[{'id':'A','text':'Drug A'},{'id':'B','text':'Drug B'}], 'key':['A'], 'evidence':[{'passage_id':'forged-generator-source'}]}
        result=audit(object(),'owner',item,textbook_id='book',context_query='topic',limit=2)
        self.assertEqual(search.call_count,3)
        self.assertTrue(result['all_options_have_matches'])
        for entry in result['option_audits']:
            self.assertEqual(len(entry['retrieved_passage_ids']),2)
            self.assertIn('topic-source',entry['retrieved_passage_ids'])
            self.assertNotIn('forged-generator-source',entry['retrieved_passage_ids'])
            self.assertEqual(entry['search_queries'],[entry['search_query'],'topic'])
        self.assertFalse(result['clinical_verification_complete']);self.assertFalse(result['can_publish'])

if __name__=='__main__':unittest.main()
