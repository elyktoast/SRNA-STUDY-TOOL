import unittest
from unittest.mock import patch
from lecture_file_to_question_plan import prepare_lecture_file_jobs

class LectureFilePlanningTests(unittest.TestCase):
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
    def test_oversize_extraction_fails_closed(self, extract):
        extract.return_value = {'format':'pdf','page_count':1,'review_pages':[],
            'requires_ocr_or_visual_review':False,
            'pages':[{'page':1,'text':'x'*12001}]}
        with self.assertRaisesRegex(ValueError,'planning limit'):
            prepare_lecture_file_jobs(None,'owner',b'data','lecture.pdf',
                textbook_id='book',item_id_factory=lambda:'id')

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

    def test_wsgi_routes_both_lecture_endpoints_to_generation(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'source_review_wsgi_v2.py').read_text()
        self.assertIn('"/generation/lecture-plan"', source)
        self.assertIn('"/generation/lecture-file-plan"', source)

if __name__ == '__main__':
    unittest.main()
