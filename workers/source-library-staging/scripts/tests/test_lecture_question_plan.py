import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lecture_question_plan import plan

PASSAGE = {"passage_id": "p1", "textbook_id": "t1", "excerpt": "Source passage"}
class LecturePlanningTests(unittest.TestCase):
    def test_balanced_grounded_coverage(self):
        topics = [{"title": "Airway"}, {"title": "Hemodynamics"}, {"title": "Airway"}]
        result = plan(topics, {"Airway": [PASSAGE], "Hemodynamics": [PASSAGE]}, count=5)
        self.assertEqual([t["question_count"] for t in result["topics"]], [3, 2])
        self.assertEqual(result["coverage"]["lecture_concepts"], 2)
        self.assertFalse(result["auto_approved"])
    def test_missing_textbook_support_is_not_generated(self):
        result = plan([{"title": "Airway"}, {"title": "Novel topic"}],
                      {"Airway": [PASSAGE]}, count=4)
        self.assertEqual(result["planned"], 4)
        self.assertEqual(result["coverage"]["uncovered_concepts"], 1)
        self.assertEqual(result["missing_textbook_support"][0]["title"], "Novel topic")
    def test_no_evidence_blocks_plan(self):
        result = plan([{"title": "Novel topic"}], {}, count=10)
        self.assertEqual(result["planned"], 0)
    def test_invalid_count_rejected(self):
        with self.assertRaises(ValueError):
            plan([{"title": "Airway"}], {"Airway": [PASSAGE]}, count=0)

if __name__ == "__main__":
    unittest.main()
