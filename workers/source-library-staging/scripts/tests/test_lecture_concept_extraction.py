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

if __name__ == "__main__":
    unittest.main()
