import io
import json
import unittest
from unittest.mock import patch
from item_generation_http_v2 import create_app
from item_saved_option_review_v2 import OptionReviewConflict
from test_item_generation_http_v2 import Connection,UID


class SavedReviewHttpTests(unittest.TestCase):
    def call(self,payload=None,method='POST',token='valid',origin='https://staging.srnastudytool.com'):
        app=create_app(conn_factory=Connection,resolve_admin=lambda t:UID if t=='valid' else None,
                       environment={'STAGING_ONLY':'true'})
        raw=json.dumps(payload or {}).encode();seen=[]
        body=b''.join(app({'PATH_INFO':'/generation/drafts/65c2e793-a7af-4746-bfb6-1abf9993085c/complete-options',
            'REQUEST_METHOD':method,'HTTP_ORIGIN':origin,'HTTP_AUTHORIZATION':'Bearer '+token,
            'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)},lambda status,headers:seen.append(status)))
        return seen[0],json.loads(body)

    @patch('item_generation_http_v2.complete_option_review',return_value={'published':False,'generation_performed':False})
    def test_explicit_confirmation_forwards_only_the_authenticated_identity(self,review):
        body={'confirm_paid_calls':True,'expected_updated_at':'saved-version'}
        status,result=self.call(body)
        self.assertEqual(status,'200 OK');self.assertFalse(result['generation_performed'])
        self.assertEqual(review.call_args.kwargs['owner_uid'],UID)
        self.assertEqual(review.call_args.kwargs['expected_updated_at'],'saved-version')

    @patch('item_generation_http_v2.complete_option_review')
    def test_unconfirmed_client_supplied_identity_or_clinical_content_never_reaches_reviewer(self,review):
        base={'confirm_paid_calls':True,'expected_updated_at':'version'}
        for body in ({},{**base,'confirm_paid_calls':False},{**base,'owner_uid':UID},{**base,'question':{}},{**base,'status':'approved_for_bank'}):
            self.assertEqual(self.call(body)[0],'422 Unprocessable Entity')
        self.assertEqual(self.call(base,token='bad')[0],'403 Forbidden')
        self.assertEqual(self.call(base,origin='https://srnastudytool.com')[0],'403 Forbidden')
        self.assertEqual(self.call(base,method='GET')[0],'405 Method Not Allowed')
        review.assert_not_called()

    @patch('item_generation_http_v2.complete_option_review',side_effect=OptionReviewConflict('private detail'))
    def test_conflict_does_not_leak_private_diagnostics(self,review):
        status,result=self.call({'confirm_paid_calls':True,'expected_updated_at':'version'})
        self.assertEqual(status,'409 Conflict')
        self.assertEqual(result,{'error':'draft_or_review_changed'})
