"""Regression tests for the full multi-book evidence handoff and its boundaries."""
import io
import json
import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import patch
from uuid import uuid4

from build_question_evidence import build_evidence
from item_source_scope_v2 import source_scope
from item_draft_review_contract_v2 import validate_draft
from item_generation_http_v2 import create_app
from lecture_generation_requests import requests, staging_http_jobs

OWNER = 'c003287a-10ce-4cc9-926e-ef7c3a162a26'
A = '6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d'
B = '8343459f-0595-4375-8ac6-7700e6792abe'


def row(book, index):
    return dict(passage_id=book+str(index), textbook_id=book, filename='test.pdf',
                excerpt='Synthetic indexed evidence', pdf_page_start=index+1, pdf_page_end=index+1)


class MultiBookTests(unittest.TestCase):
    def test_fair_packet_retains_each_source_and_physical_page(self):
        def search(conn, query, owner, **kw):
            self.assertEqual(owner, OWNER)
            return [row(kw['textbook_id'], i) for i in range(4)]
        with patch('build_question_evidence.search', side_effect=search) as lookup:
            packet = build_evidence(object(), OWNER, 'ventilation', textbook_id=A,
                                    textbook_ids=[B, A], limit=4)
        self.assertEqual([p['textbook_id'] for p in packet['sources']], [A, B, A, B])
        self.assertEqual([p['pdf_page_start'] for p in packet['sources']], [1, 1, 2, 2])
        self.assertTrue(all(p['citation_verified'] is False for p in packet['sources']))
        self.assertEqual(lookup.call_count, 2)

    def test_invalid_scopes_and_book_specific_filters_fail_before_retrieval(self):
        for books in ([], [A, A], [B], [A.upper(), B], [A, 'bad'], 'all', [A]*9):
            with self.subTest(books=books), self.assertRaises(ValueError):
                source_scope(A, books)
        for options in ({'page_start':1}, {'page_end':2}, {'section_id':A}, {'limit':1}):
            with patch('build_question_evidence.search') as lookup:
                with self.assertRaises(ValueError):
                    build_evidence(object(), OWNER, 'airway', textbook_id=A, textbook_ids=[A,B], **options)
                lookup.assert_not_called()

    def test_empty_primary_fails_before_any_paid_generation(self):
        with patch('build_question_evidence.search', side_effect=[[], [row(B,0)]]):
            with self.assertRaisesRegex(ValueError, 'primary textbook'):
                build_evidence(object(), OWNER, 'airway', textbook_id=A, textbook_ids=[A,B])

    def test_lecture_all_books_survive_the_executable_handoff(self):
        plan = {'topics':[{'title':'malignant hyperthermia', 'question_count':1,
                           'evidence':[row(A,0), row(B,0)]}]}
        prepared = requests(plan, mode='NCE')
        job = staging_http_jobs(prepared, textbook_id=None, item_id_factory=lambda:str(uuid4()))['jobs'][0]
        self.assertEqual(job['body']['textbook_ids'], [A,B])
        self.assertEqual(job['path'], '/generation/preflight')
        single = staging_http_jobs(prepared, textbook_id=A, item_id_factory=lambda:str(uuid4()))['jobs'][0]
        self.assertNotIn('textbook_ids', single['body'])

    def test_draft_requires_explicit_scope_and_primary_evidence(self):
        payload = dict(owner_uid=OWNER,textbook_id=A,mode='NCE',format='MC',
                       question={},screening={},evidence=[row(A,0),row(B,0)])
        with self.assertRaises(ValueError):
            validate_draft(payload)
        result = validate_draft({**payload,'textbook_ids':[A,B]})
        self.assertFalse(result['published'])
        with self.assertRaisesRegex(ValueError, 'Primary textbook'):
            validate_draft({**payload,'textbook_ids':[A,B],'evidence':[row(B,0)]})

    def test_authenticated_preflight_normalizes_scope_and_rejects_physical_page_mix(self):
        class Conn:
            def __enter__(self): return self
            def __exit__(self,*args): return False
        app = create_app(conn_factory=Conn,resolve_admin=lambda token:OWNER,environment={'STAGING_ONLY':'true'})
        body = dict(topic='ventilation',textbook_id=A,textbook_ids=[B,A],mode='NCE',format='MC',
                    domain='I',section='A',objective='I.A.2',item_id=str(uuid4()))
        def call(payload):
            raw=json.dumps(payload).encode(); status=[]
            response=b''.join(app({'PATH_INFO':'/generation/preflight','REQUEST_METHOD':'POST',
                'HTTP_ORIGIN':'https://staging.srnastudytool.com','HTTP_AUTHORIZATION':'Bearer valid',
                'CONTENT_LENGTH':str(len(raw)),'wsgi.input':io.BytesIO(raw)},lambda s,h:status.append(s)))
            return status[0],json.loads(response)
        with patch('item_generation_http_v2.execute',return_value={'dry_run':True}) as run:
            self.assertEqual(call(body)[0],'200 OK')
            self.assertEqual(run.call_args.args[1].textbook_ids,[A,B])
            run.reset_mock()
            self.assertEqual(call({**body,'page_start':1})[0],'400 Bad Request')
            run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
