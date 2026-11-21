import copy
import json
import unittest
from unittest.mock import patch
from item_saved_option_review_v2 import complete_option_review, eligible, OptionReviewConflict
from test_item_draft_review_contract_v2 import passed_screening, OWNER, BOOK

DID='65c2e793-a7af-4746-bfb6-1abf9993085c'
ENV={'STAGING_ONLY':'true','AI_OPTION_REVIEW_OPT_IN':'true','AI_GENERATOR_MODEL':'author','AI_REVIEWER_MODEL':'reviewer'}
SOURCE={'passage_id':'p1','textbook_id':BOOK,'pdf_page_start':1,
        'excerpt':'Alpha resolves condition X. Beta, Gamma and Delta do not resolve condition X.'}


def saved():
    screening=passed_screening()
    screening['stages']['independent_option_evidence']={'status':'pending','issues':[]}
    screening.update(rewrite_attempts_used=1,rewrite_attempts_allowed=0,pending_verifications=['independent_option_evidence','human_review'])
    return {'draft_id':DID,'format':'MC','status':'pending_review','published':False,'updated_at':'2026-11-17T00:00:00+00:00',
            'textbook_id':BOOK,'model':'author','topic':'Explain condition X','screening':screening,'evidence':[SOURCE],
            'question':{'model':'author','format':'MC','stem':'Which response resolves condition X?', 'key':['A'],
                'options':[{'id':i,'text':t} for i,t in zip('ABCD',['Alpha','Beta','Gamma','Delta'])],
                'evidence':[SOURCE]}}


class Cursor:
    def __init__(self,rows):self.rows=list(rows);self.calls=[]
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def execute(self,sql,params):self.calls.append((sql,params))
    def fetchone(self):return self.rows.pop(0)


class Conn:
    def __init__(self,rows=None):self.cur=Cursor([(True,),(False,),(DID,)] if rows is None else rows)
    def cursor(self):return self.cur


class SavedOptionReviewTests(unittest.TestCase):
    def execute(self,draft=None,*,rows=None,judgments=None,validation=None):
        draft=saved() if draft is None else draft
        conn=Conn(rows)
        calls=[]
        def reviewer(payload):
            calls.append(payload)
            if judgments is not None:return judgments
            return [{'option_id':i,'verdict':'supports_key' if i=='A' else 'refutes_distractor',
                'passage_ids':['p1'],'quotes':[SOURCE['excerpt']], 'explanation':'The source distinguishes these responses.',
                'contradiction_found':False} for i in 'ABCD']
        with patch('item_saved_option_review_v2.get_draft',return_value=draft), \
             patch('item_saved_option_review_v2.revalidate',return_value={'issues':validation if validation is not None else [{'field':'screening.stages.independent_option_evidence'}]}), \
             patch('item_option_retrieval_audit_v2.search',return_value=[SOURCE]), \
             patch('item_saved_option_review_v2.search',return_value=[SOURCE]):
            result=complete_option_review(conn,owner_uid=OWNER,draft_id=DID,
                expected_updated_at=draft['updated_at'],environment=ENV,reviewer_factory=lambda:reviewer)
        return result,conn,calls

    def test_completes_only_missing_review_without_modifying_question_rewrite_or_human_state(self):
        draft=saved();original=copy.deepcopy(draft)
        result,conn,calls=self.execute(draft)
        self.assertTrue(result['automated_checks_passed'])
        self.assertEqual(result['option_review_status'],'pass')
        self.assertEqual(draft,original)
        self.assertEqual(len(calls),1)
        self.assertNotIn('key',calls[0]);self.assertNotIn('rationale',calls[0])
        self.assertNotIn('expected_verdict',str(calls[0]))
        query,params=conn.cur.calls[-1]
        self.assertIn('d.question_json=%s::jsonb',query)
        self.assertIn('d.screening_json=%s::jsonb',query)
        self.assertIn('generated_draft_revisions_v2',query)
        self.assertIn('left(p.content,1600)',query)
        self.assertNotIn('set question_json',query)
        updated=json.loads(params[0])
        self.assertEqual(updated['rewrite_attempts_used'],1)
        self.assertEqual(updated['rewrite_attempts_allowed'],0)
        self.assertEqual(updated['stages']['human_review'],original['screening']['stages']['human_review'])
        for name,stage in original['screening']['stages'].items():
            if name!='independent_option_evidence':self.assertEqual(updated['stages'][name],stage)
        for key in ('question_modified','generation_performed','rewrite_performed','published','can_publish'):
            self.assertFalse(result[key])
        self.assertTrue(result['clinical_review_required'])

    def test_flagged_or_edited_or_completed_drafts_do_not_get_a_new_grade(self):
        for change in ('cue','explanations','missing_stage','bad_index','clinical_judgment','format','status','complete','malformed'):
            draft=saved()
            if change in ('cue','explanations'):
                draft['screening']['stages']['options_only' if change=='cue' else 'explanation_evidence']['status']='flag'
            if change=='missing_stage':del draft['screening']['stages']['blind_model']
            if change=='bad_index':draft['screening']['stages']['duplicates'].pop('index_id')
            if change=='clinical_judgment':draft['screening']['independent_option_adjudication']={'judgments':[{'verdict':'uncertain'}]}
            if change=='format':draft['format']='MS'
            if change=='status':draft['status']='needs_revision'
            if change=='complete':draft['screening']['stages']['independent_option_evidence']['status']='pass'
            if change=='malformed':draft['screening']['stages']=None
            with self.subTest(change=change):
                self.assertFalse(eligible(draft))
                with self.assertRaises(ValueError):self.execute(draft)

    def test_busy_review_and_concurrent_revision_or_source_change_cannot_save_a_pass(self):
        for rows in ([(False,)],[(True,),(True,)],[(True,),(False,),None]):
            with self.subTest(rows=rows),self.assertRaises(OptionReviewConflict):self.execute(rows=rows)

    def test_current_source_failures_block_before_the_model(self):
        with self.assertRaises(ValueError):self.execute(validation=[{'rule_id':'R-2.5','message':'Source changed'}])

    def test_invalid_quotes_remain_pending_and_are_not_retryable_clinical_judgments(self):
        judgments=[{'option_id':i,'verdict':'supports_key' if i=='A' else 'refutes_distractor',
            'passage_ids':['p1'],'quotes':['Fabricated quotation that is absent'],
            'explanation':'Source claim.','contradiction_found':False} for i in 'ABCD']
        result,conn,_=self.execute(judgments=judgments)
        self.assertEqual(result['option_review_status'],'pending')
        self.assertFalse(result['automated_checks_passed'])
        draft=saved();draft['screening']=json.loads(conn.cur.calls[-1][1][0])
        self.assertFalse(eligible(draft))

    def test_stale_timestamp_or_missing_opt_in_never_calls_provider(self):
        draft=saved();conn=Conn()
        with patch('item_saved_option_review_v2.get_draft',return_value=draft):
            with self.assertRaises(OptionReviewConflict):complete_option_review(conn,owner_uid=OWNER,draft_id=DID,
                expected_updated_at='stale',environment=ENV,reviewer_factory=lambda:self.fail('No paid call'))
        with self.assertRaises(ValueError):complete_option_review(Conn(),owner_uid=OWNER,draft_id=DID,
            expected_updated_at=draft['updated_at'],environment={'STAGING_ONLY':'true'},reviewer_factory=lambda:self.fail('No paid call'))

    def test_reviewing_model_must_differ_from_the_original_author_not_just_current_settings(self):
        draft=saved();draft['model']='reviewer';draft['question']['model']='reviewer'
        with self.assertRaises(ValueError):self.execute(draft)

    def test_provider_adapter_is_bound_to_independent_option_review(self):
        from item_saved_option_review_v2 import configured_reviewer
        env={**ENV,'AI_PROVIDER_ENDPOINT':'https://provider.example/v1','AI_ALLOWED_HOSTS':'provider.example',
             'AI_PROVIDER_API_KEY':'test','STAGING_RECEIPT_SIGNING_SECRET':'x'*48}
        with patch('item_saved_option_review_v2.make_transport') as transport, \
             patch('item_saved_option_review_v2.make_adapter') as adapter:
            adapter.return_value.return_value={'judgments':[{'source_conflict_found':False}]}
            reviewer=configured_reviewer(env)
            result=reviewer({'format':'MC'})
        self.assertEqual(adapter.call_args.kwargs['model'],'reviewer')
        self.assertEqual(transport.call_args.kwargs['timeout_seconds'],50)
        payload=adapter.return_value.call_args.args[0]
        self.assertEqual(payload['step'],'option_review')
        self.assertTrue(payload['blind']);self.assertFalse(payload['auto_publish'])
        self.assertFalse(result[0]['contradiction_found'])
