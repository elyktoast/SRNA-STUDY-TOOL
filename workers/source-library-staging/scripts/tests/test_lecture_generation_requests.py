import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lecture_generation_requests import requests

class LectureRequestTests(unittest.TestCase):
    def test_grounded_slots(self):
        p = {"topics": [{"title": "Airway", "lecture_locator": "slide 4",
                         "question_count": 2, "evidence": [{
                             "passage_id": "p1", "textbook_id": "t1",
                             "excerpt": "Grounded text"}]}]}
        result = requests(p, mode="NCE", domain="III",
                          section="III.H", objective="III.H.4")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["requests"][0]["concept_request"]["step"], "concept_card")
        self.assertEqual(result["requests"][0]["lecture_locator"], "slide 4")
        self.assertFalse(result["auto_generate"])
    def test_missing_evidence_rejected(self):
        p = {"topics": [{"title": "Unsupported", "question_count": 1, "evidence": []}]}
        with self.assertRaises(ValueError):
            requests(p, mode="NCE", domain="III",
                     section="III.H", objective="III.H.4")

if __name__ == "__main__":
    unittest.main()
