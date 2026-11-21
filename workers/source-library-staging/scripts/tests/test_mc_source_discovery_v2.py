import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
from item_mc_source_discovery_v2 import discover
from item_ai_provider_v2 import make_adapter


class SourceDiscoveryTests(unittest.TestCase):
    def args(self):
        return SimpleNamespace(topic='Selected teaching point',owner_uid='owner',textbook_id='book1',
            textbook_ids=['book1','book2'],section_id='section',include_subsections=True,page_start=10,page_end=20)

    def test_bounded_diverse_searches_preserve_every_scope_and_original_evidence(self):
        packet={'sources':[{'passage_id':'original','textbook_id':'book1'}],'topic':'Selected teaching point'}
        before=deepcopy(packet)
        requests=[]
        def planner(p):
            requests.append(p);return {'queries':['Concept A','Concept B','Concept C','Concept D']}
        def retrieve(conn,owner,q,**scope):
            return {'sources':[{'passage_id':q+scope['textbook_id']+str(i),'textbook_id':scope['textbook_id']}
                               for i in range(2)]}
        with patch('item_mc_source_discovery_v2.build_evidence',side_effect=retrieve) as search:
            result,metadata=discover(None,self.args(),packet,planner)
        self.assertEqual(len(search.call_args_list),8)
        self.assertEqual(metadata['passage_ids'],['Concept '+q+'book10' for q in 'ABCD'])
        for call in search.call_args_list:
            self.assertEqual(call.args[1],'owner')
            self.assertEqual({k:v for k,v in call.kwargs.items() if k!='textbook_id'},
                dict(limit=2,section_id='section',include_subsections=True,page_start=10,page_end=20))
        self.assertEqual(packet,before)
        self.assertEqual(result['sources'][0],before['sources'][0])
        self.assertEqual(len(result['sources']),5)
        self.assertEqual(set(requests[0]),{'step','rules_version','auto_publish','format','topic'})
        self.assertFalse(metadata['clinical_truth_verified'])
        self.assertFalse(metadata['database_writes'])

    def test_bad_search_plan_fails_before_database_or_draft_calls(self):
        for response in ({}, {'queries':[]}, {'queries':['x']}, {'queries':['word']*5},
                         {'queries':['valid'],'answer_key':'A'}):
            with self.subTest(response=response),patch('item_mc_source_discovery_v2.build_evidence') as search:
                with self.assertRaises(ValueError): discover(None,self.args(),{'sources':[]},lambda _:response)
                search.assert_not_called()

    def test_foreign_book_candidate_is_rejected(self):
        with patch('item_mc_source_discovery_v2.build_evidence',return_value={
                'sources':[{'passage_id':'foreign','textbook_id':'not-selected'}]}):
            with self.assertRaises(ValueError):
                discover(None,self.args(),{'sources':[]},lambda _:{'queries':['Concept A']})

    def test_search_planner_has_a_small_separate_budget_and_no_authority(self):
        captured=[]
        def transport(**kw):
            captured.append(kw['body']);return {'choices':[{'message':{'content':'{"queries":["Concept A"]}'}}]}
        adapter=make_adapter(endpoint='https://api.groq.com/openai/v1/chat/completions',api_key='fixture',
            model='author',transport=transport,owner_opt_in=True,staging=True,max_output_tokens=8192)
        adapter({'step':'retrieval_plan','rules_version':'2.0','auto_publish':False,'format':'MC','topic':'Topic'})
        self.assertEqual(captured[0]['max_tokens'],512)
        with self.assertRaises(ValueError):
            adapter({'step':'retrieval_plan','rules_version':'2.0','auto_publish':False,'format':'MS','topic':'Topic'})
