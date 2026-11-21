import unittest
from unittest.mock import patch
from lecture_file_to_question_plan import prepare_lecture_file_jobs

class LectureFilePlanningTests(unittest.TestCase):
    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_focused_jobs_keep_parent_emphasis_priority(self, extract):
        extract.return_value={'format':'pdf','page_count':1,'review_pages':[],
                              'pages':[{'page':1,'text':'Slide text'}]}
        jobs=[{'body':{'topic':name+' — Specific teaching point'},'lecture_topic':name}
              for name in ('Standard topic','Highlighted topic')]
        plan={'jobs':jobs,'count':2,'lecture_plan':{'topics':[
            {'title':'Standard topic','importance':'standard'},
            {'title':'Highlighted topic','importance':'highlighted'}]}}
        with patch('lecture_to_question_plan.prepare_staging_jobs',return_value=plan):
            result=prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                       textbook_id='book',item_id_factory=lambda:'id',count=2)
        self.assertEqual(result['jobs'][0]['lecture_topic'],'Highlighted topic')

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_emphasis_summary_only_reports_selected_pages_without_exposing_lecture_text(self, extract):
        extract.return_value={'format':'pdf','page_count':3,'review_pages':[], 'pages':[
            {'page':1,'text':'First topic','emphasis':{'highlighted':['Highlighted private phrase'],'bold':[]}},
            {'page':2,'text':'Second topic','emphasis':{'highlighted':[],'bold':['Bold private phrase']}},
            {'page':3,'text':'Third topic','emphasis':{'highlighted':['Unselected private phrase'],'bold':['Another phrase']}}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',return_value={'jobs':[],'count':0}):
            result=prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',textbook_id='book',
                item_id_factory=lambda:'id',page_start=1,page_end=2)
        self.assertEqual(result['file_extraction']['emphasis_pages'],{'highlighted':[1],'bold':[2]})
        self.assertNotIn('private phrase',str(result['file_extraction']))
        self.assertFalse(result['auto_generate'])
        self.assertFalse(result['auto_publish'])

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_short_lecture_honors_requested_question_count(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[],
                                'pages':[{'page':1,'text':'Local anesthetic ionization'}]}
        jobs = [{'path':'/generation/preflight','body':{'item_id':str(n)}} for n in range(3)]
        with patch('lecture_to_question_plan.prepare_staging_jobs', return_value={'jobs':jobs,'count':3}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',textbook_id='book',
                                               item_id_factory=lambda:'id',count=3)
        self.assertEqual(planner.call_args.kwargs['count'],3)
        self.assertEqual(result['count'],3)
        self.assertEqual(result['jobs'],jobs)

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_multiple_chunks_share_the_requested_budget(self, extract):
        extract.return_value = {'format':'pdf','page_count':2,'review_pages':[],
            'pages':[{'page':n,'text':'Local anesthetic ionization\n'+'x '*4500} for n in (1,2)]}
        def plan(*args,**kwargs):
            chunk = 'first' if 'Page 1:' in args[2] else 'second'
            return {'jobs':[{'chunk':chunk,'slot':n} for n in range(kwargs['count'])], 'count':kwargs['count']}
        with patch('lecture_to_question_plan.prepare_staging_jobs',side_effect=plan):
            result=prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',textbook_id='book',
                                             item_id_factory=lambda:'id',count=3)
        self.assertEqual([(j['chunk'],j['slot']) for j in result['jobs']],
                         [('first',0),('second',0),('first',1)])
        self.assertEqual(result['count'],3)

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_image_pages_hold_without_textbook_query(self, extract):
        extract.return_value = {'format':'pptx','page_count':2,
            'review_pages':[2],'requires_ocr_or_visual_review':True,'pages':[]}
        with patch('lecture_to_question_plan.prepare_staging_jobs') as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','slides.pptx',
                textbook_id='book',item_id_factory=lambda:'id')
            planner.assert_not_called()
        self.assertEqual(result['held_reason'],'visual_review_required')
        self.assertEqual(result['file_extraction']['review_pages'],[2])
        self.assertFalse(result['auto_generate'])

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_clean_pages_flow_to_existing_planner(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,
            'review_pages':[],'requires_ocr_or_visual_review':False,
            'pages':[{'page':1,'text':'Airway anatomy learning objective'}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0,'auto_generate':False}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
        self.assertIn('Airway anatomy',planner.call_args.args[2])
        self.assertFalse(result['file_extraction']['requires_visual_review'])

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_long_lecture_is_chunked_without_truncation(self, extract):
        source = "airway management " * 1500
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[],
            'pages':[{'page':1,'text':source}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0,'auto_generate':False}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
        self.assertGreater(result['chunk_count'], 1)
        self.assertEqual(planner.call_count, result['processed_chunk_count'])
        self.assertTrue(all(len(call.args[2]) <= 12000 for call in planner.call_args_list))
        self.assertFalse(result['auto_generate'])

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_oversize_extraction_fails_closed(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[],
            'requires_ocr_or_visual_review':False,
            'pages':[{'page':1,'text':'x'*12001}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0,'auto_generate':False}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
        self.assertEqual(result['chunk_count'], 2)
        self.assertEqual(planner.call_count, 2)

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_range_excludes_unselected_visual_pages(self, extract):
        extract.return_value = {'format':'pdf','page_count':3,'review_pages':[3],
            'requires_ocr_or_visual_review':True,
            'pages':[{'page':1,'text':'Airway anatomy','needs_visual_review':False},
                     {'page':2,'text':'Laryngoscopy','needs_visual_review':False},
                     {'page':3,'text':'Diagram','needs_visual_review':True}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id',page_start=1,page_end=2)
        self.assertEqual(result['file_extraction']['selected_pages'],[1,2])
        self.assertNotIn('Diagram',planner.call_args.args[2])

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_range_must_be_complete_and_bounded(self, extract):
        extract.return_value = {'format':'pdf','page_count':2,'pages':[],
            'requires_ocr_or_visual_review':False}
        for start,end in [(1,None),(0,1),(2,1),(1,3),(True,1)]:
            with self.subTest(start=start,end=end),self.assertRaises(ValueError):
                prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                    textbook_id='book',item_id_factory=lambda:'id',
                    page_start=start,page_end=end)

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_blank_page_is_skipped_but_image_only_page_is_held(self, extract):
        extract.return_value = {'format':'pdf','page_count':2,'review_pages':[1],
            'pages':[{'page':1,'text':'','needs_visual_review':True,'image_count':0,'vector_count':0},
                     {'page':2,'text':'Airway anatomy','needs_visual_review':False}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
        self.assertEqual(result['file_extraction']['skipped_blank_pages'],[1])
        self.assertFalse(result['file_extraction']['requires_visual_review'])
        self.assertIn('Airway anatomy',planner.call_args.args[2])
        extract.return_value['pages'][0]['image_count'] = 1
        with patch('lecture_to_question_plan.prepare_staging_jobs') as planner:
            held = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
            planner.assert_not_called()
        self.assertEqual(held['held_reason'],'visual_review_required')

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_text_with_diagram_plans_text_only_and_flags_visual(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[1],
            'pages':[{'page':1,'text':'Text on volatile anesthetic uptake',
                      'needs_visual_review':True,'vector_count':3}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0,'auto_generate':False}) as planner:
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
        self.assertIn('volatile anesthetic uptake',planner.call_args.args[2])
        self.assertEqual(result['file_extraction']['text_only_visual_pages'],[1])
        self.assertEqual(result['file_extraction']['review_pages'],[])

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_zero_jobs_exposes_aggregate_failure_counts(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[],
            'pages':[{'page':1,'text':'Airway management'}]}
        plan = {'jobs':[],'count':0,'classification':{'held_count':0},
                'lecture_plan':{'coverage':{'lecture_concepts':1,
                    'grounded_concepts':0,'uncovered_concepts':1}}}
        with patch('lecture_to_question_plan.prepare_staging_jobs', return_value=plan):
            result = prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')
        self.assertEqual(result['planning_diagnostics']['extracted_concepts'],1)
        self.assertEqual(result['planning_diagnostics']['grounded_concepts'],0)
        self.assertEqual(result['planning_diagnostics']['missing_textbook_support'],1)

    @patch('lecture_file_to_question_plan.extract_lecture')
    def test_all_indexed_books_passes_unrestricted_evidence_scope(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[],
            'pages':[{'page':1,'text':'Breathing circuits'}]}
        with patch('lecture_to_question_plan.prepare_staging_jobs',
                   return_value={'jobs':[],'count':0,'classification':{'held_count':0}}) as planner:
            prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id=None,item_id_factory=lambda:'id')
        self.assertIsNone(planner.call_args.kwargs['textbook_id'])

    def test_wsgi_routes_both_lecture_endpoints_to_generation(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'source_review_wsgi_v2.py').read_text()
        self.assertIn('"/generation/lecture-plan"', source)
        self.assertIn('"/generation/lecture-file-plan"', source)

if __name__ == '__main__':
    unittest.main()
