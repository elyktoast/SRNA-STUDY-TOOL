"""Offline regressions for slide scope and failed blind-case repairs."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4

from lecture_concept_extraction import extract
from lecture_to_question_plan import prepare_staging_jobs
from build_question_evidence import build_evidence, lecture_focus_queries
from item_rewrite_once_v2 import attempt_once
import test_rewrite_answer_integrity_v2 as integrity_fixture


class LectureFocusTests(unittest.TestCase):
    def test_teaching_points_stay_with_heading_and_page(self):
        result = extract('Page 14:\n# Monitoring: Motion\n• Measures acceleration of the thumb\n'
            'Monitoring: Electrical\n• Oldest method\n• Measures electrical response\n'
            'of muscle (action potential)\n• Requires additional electrodes\n'
            'Lecture bold: Monitoring: Electrical\nPage 15:\n• Unrelated later page bullet')
        topics = {c['title']: c for c in result['concepts']}
        self.assertEqual(topics['Monitoring: Motion']['learning_points'],
                         ['Measures acceleration of the thumb'])
        self.assertEqual(topics['Monitoring: Electrical']['learning_points'],
                         ['Measures electrical response of muscle (action potential)',
                          'Requires additional electrodes'])
        self.assertEqual(result['concepts'][0]['importance'], 'bold')

    def test_focused_jobs_rotate_points_and_preserve_parent_classification(self):
        title = 'Quantitative Monitoring: Electromyography'
        points = ['Record the evoked muscle action potential', 'Use additional recording electrodes']
        text = '# '+title+'\n'+''.join('• '+p+'\n' for p in points)+'Lecture bold: '+title
        with patch('lecture_to_question_plan.build_evidence', return_value={'sources':[
                {'passage_id':'p1','textbook_id':'t1','excerpt':'Textbook evidence'}]}):
            result = prepare_staging_jobs(None, 'owner', text, textbook_id='t1',
                item_id_factory=lambda:str(uuid4()), count=3, domain='II', section='C', objective='II.C.4')
        self.assertEqual([j['body']['topic'] for j in result['jobs']],
                         [title+' — '+points[i%2] for i in range(3)])
        self.assertTrue(all(j['lecture_topic']==title and j['body']['objective']=='II.C.4'
                            for j in result['jobs']))
        self.assertFalse(result['auto_generate'])
        self.assertFalse(result['database_writes'])
        self.assertNotIn('learning_points', result['lecture_plan']['topics'][0])

    def test_large_mc_plan_checks_focuses_directly_and_queues_each_supported_focus_once(self):
        book = str(uuid4())
        owner = str(uuid4())
        row = {"passage_id": "p1", "textbook_id": book, "filename": "example.pdf",
               "pdf_page_start": 1, "pdf_page_end": 1, "excerpt": "Indexed fixture."}
        lecture = ("# Monitoring: Electrical\n• Record the evoked muscle action potential\n"
                   "• Use additional recording electrodes\n"
                   "Lecture highlighted: Monitoring: Electrical\n"
                   "# Monitoring: Motion\n• Measure acceleration of the thumb")
        calls = []
        def lookup(conn, uid, requests):
            self.assertEqual(uid, owner)
            calls.extend(requests)
            return [[row] if "potential" in term or term.startswith("motion ") else [] for term, _ in requests]
        with patch("lecture_to_question_plan.supports_pipeline", return_value=True), \
             patch("lecture_to_question_plan.search_many", side_effect=lookup):
            result = prepare_staging_jobs(None, owner, lecture, textbook_id=book, count=25,
                item_id_factory=lambda:str(uuid4()), domain="II", section="C", objective="II.C.4")
        self.assertEqual(len(calls), len({term for term, _ in calls}))
        self.assertGreater(len(calls), 3)
        self.assertTrue(any(term.startswith("motion ") for term, _ in calls))
        self.assertTrue(all(scope == {"textbook_id": book, "limit": 6} for _, scope in calls))
        self.assertEqual(result["lecture_plan"]["focus_preflight"], {"checked": 3, "grounded": 2, "held": 1})
        jobs = result["jobs"]
        self.assertEqual(len(jobs), 2)
        self.assertTrue(jobs[0]["body"]["topic"].startswith("Monitoring: Electrical — "))
        self.assertTrue(all("electrodes" not in job["body"]["topic"] for job in jobs))
        self.assertTrue(all("evidence" not in job["body"] for job in jobs))

    def test_fallback_preserves_owner_book_section_and_pages(self):
        topic = 'Quantitative Monitoring: Electromyography — Record the evoked muscle action potential'
        scope = dict(textbook_id='8343459f-0595-4375-8ac6-7700e6792abe', section_id='section',
                     include_subsections=True, page_start=10, page_end=20, limit=3)
        owner='c003287a-10ce-4cc9-926e-ef7c3a162a26'
        conn=object()
        with patch('build_question_evidence.search', return_value=[]) as lookup:
            result=build_evidence(conn,owner,topic,**scope)
        self.assertEqual([c.args[1] for c in lookup.call_args_list],
                         [topic, *lecture_focus_queries('Quantitative Monitoring: Electromyography',
                                                       'Record the evoked muscle action potential'), 'Electromyography'])
        for call in lookup.call_args_list:
            self.assertEqual(call.args[0],conn)
            self.assertEqual(call.args[2],owner)
            self.assertEqual(call.kwargs,scope)
        self.assertEqual(result['topic'],topic)
        self.assertFalse(result['can_generate_grounded_questions'])

    def test_first_supported_query_stops_fallback(self):
        row={'passage_id':'p1','textbook_id':'t1','filename':'book.pdf',
             'pdf_page_start':1,'pdf_page_end':1,'excerpt':'Grounded evidence'}
        with patch('build_question_evidence.search', return_value=[row]) as lookup:
            build_evidence(object(),'owner','Heading — Focused teaching point')
        lookup.assert_called_once()


class CounterfactualRepairTests(unittest.TestCase):
    def test_unchanged_failed_blind_case_cannot_be_resampled_or_rekeyed(self):
        fixture=integrity_fixture.RewriteAnswerIntegrityTests(); fixture.setUp()
        original=fixture.item
        original['stem']='The device uses method X. Which response is recorded?'
        original['concept_card']['counterfactual']='If "method X" is replaced by "method Y", the best response changes to option(s) B.'
        issues=[{'rule_id':'R-5.3','stem_change':{'from_text':'method X','to_text':'method Y'},
                 'independent_key':['D'],'expected_key':['B']}]
        for change in ('rationale','expected_key','whitespace'):
            candidate=deepcopy(original)
            if change=='rationale': candidate['rationale']={'why_key_wins':'Revised rationale'}
            if change=='expected_key':
                candidate['concept_card']['counterfactual']=candidate['concept_card']['counterfactual'].replace('option(s) B','option(s) D')
            if change=='whitespace': candidate['stem']=candidate['stem'].replace('Which response','Which  response')
            with self.subTest(change=change):
                result=attempt_once(original,issues,lambda _:candidate,
                                    lambda _:self.fail('Unchanged failed case must not be reviewed again'))
                self.assertTrue(result['rewrite_failed'])
                self.assertFalse(result['can_publish'])
                self.assertEqual(result['item'],original)
        candidate=deepcopy(original)
        candidate['concept_card']['counterfactual']=candidate['concept_card']['counterfactual'].replace('method Y','method Z')
        calls=[]
        result=attempt_once(original,issues,lambda _:candidate,lambda value:calls.append(value) or [])
        self.assertEqual(len(calls),1)
        self.assertEqual(result['item'],candidate)
        self.assertFalse(result['can_publish'])
