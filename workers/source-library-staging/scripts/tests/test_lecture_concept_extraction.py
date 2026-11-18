import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lecture_concept_extraction import extract
from lecture_to_question_plan import prepare

class LectureExtractionTests(unittest.TestCase):
    def test_headings_and_objectives(self):
        text = "Slide 2\n# Airway management\nObjectives:\n- Describe airway assessment\n- Identify aspiration risks\n\n# Airway management"
        result = extract(text)
        self.assertEqual([x["title"] for x in result["concepts"]],
                         ["Airway management", "Describe airway assessment", "Identify aspiration risks"])
        self.assertEqual(result["concepts"][0]["lecture_locator"], "slide/page 2")
        self.assertTrue(result["requires_review"])
    def test_file_planner_page_prefix_with_colon(self):
        result = extract("Page 1:\nBREATHING CIRCUITS, HUMIDIFICATION/FILTRATION AND CLOSED CIRCUIT\nAdditional notes")
        self.assertEqual(len(result["concepts"]), 1)
        self.assertEqual(result["concepts"][0]["lecture_locator"], "slide/page 1")
        self.assertIn("BREATHING CIRCUITS", result["concepts"][0]["title"])

    def test_plain_text_does_not_invent_concepts(self):
        self.assertEqual(extract("This is a narrative lecture with no explicit headings.")["concepts"], [])
    def test_private_retrieval_plans_only_grounded_concepts(self):
        with patch("lecture_to_question_plan.build_evidence") as lookup:
            lookup.side_effect = lambda conn, owner, topic, **kw: {
                "sources": ([{"passage_id": "p", "textbook_id": "t", "excerpt": "text"}]
                            if topic == "Airway management" else [])}
            result = prepare(None, "owner", "# Airway management\n# Novel concept", count=4)
        self.assertEqual(result["planned"], 4)
        self.assertEqual(result["coverage"]["uncovered_concepts"], 1)
        self.assertFalse(result["database_writes"])
    def test_invalid_input_rejected(self):
        with self.assertRaises(ValueError):
            extract("")

    def test_markdown_and_plain_objective_headers_never_become_clinical_topics(self):
        title='Compare intrapulmonary shunt and alveolar dead space in terms of alveolar ventilation and pulmonary perfusion.'
        for heading in ('# Learning objectives','## Learning Objectives:','Learning objectives','Objectives:'):
            for gap in ('\n','\n\n'):
                with self.subTest(heading=heading,gap=gap):
                    result=extract(heading+gap+'- '+title)
                    self.assertEqual([c['title'] for c in result['concepts']],[title])
                    self.assertEqual(result['concepts'][0]['importance'],'learning_objective')
        result=extract('# Learning objectives\n- Identify aspiration risks\n\nNarrative explanation.\n- Unrelated later bullet\n# Respiratory mechanics')
        self.assertEqual([c['title'] for c in result['concepts']],['Identify aspiration risks','Respiratory mechanics'])

    def test_generic_objective_heading_is_not_retrieved_or_allocated(self):
        title='Compare shunt and dead space'
        with patch('lecture_to_question_plan.build_evidence') as lookup:
            lookup.return_value={'sources':[{'passage_id':'p','textbook_id':'t','excerpt':'Respiratory source'}]}
            result=prepare(None,'owner','# Learning objectives\n\n- '+title,count=1,prefer_learning_objectives=True)
        self.assertEqual([c.args[2] for c in lookup.call_args_list],[title])
        self.assertEqual(result['topics'][0]['title'],title)
        self.assertEqual(result['topics'][0]['question_count'],1)

if __name__ == "__main__":
    unittest.main()
