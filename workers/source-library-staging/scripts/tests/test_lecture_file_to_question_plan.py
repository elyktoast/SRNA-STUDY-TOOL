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

if __name__ == '__main__':
    unittest.main()
