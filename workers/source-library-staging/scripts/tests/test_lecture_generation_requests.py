import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lecture_generation_requests import requests, staging_http_jobs
from unittest.mock import patch
from uuid import uuid4

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

class LectureHandoffTests(unittest.TestCase):
    def sample(self, title="malignant hyperthermia", count=1):
        return {"topics": [{"title": title, "question_count": count,
            "evidence": [{"passage_id": "p1", "textbook_id": "t1",
                          "excerpt": "Grounded textbook evidence"}]}]}

    def test_candidate_and_preflight(self):
        prepared = requests(self.sample(), mode="NCE")
        self.assertEqual(prepared["count"], 1)
        self.assertFalse(prepared["requests"][0]["classification"]["verified"])
        jobs = staging_http_jobs(prepared, textbook_id="t1",
                                 item_id_factory=lambda: str(uuid4()))
        self.assertEqual(jobs["jobs"][0]["path"], "/generation/preflight")
        self.assertEqual(jobs["jobs"][0]["body"]["topic"], "malignant hyperthermia")
        self.assertFalse(jobs["jobs"][0]["body"]["execute"])
        self.assertFalse(jobs["jobs"][0]["body"]["confirm_paid_calls"])

    def test_unclassified_topic_held(self):
        result = requests(self.sample("unrecognized concept xyz"), mode="SEE")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["held_count"], 1)

    def test_ambiguous_topic_held(self):
        with patch("lecture_generation_requests.suggest", return_value={
                "status": "ambiguous", "candidates": [], "requires_review": True}):
            result = requests(self.sample(), mode="NCE")
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["held_count"], 1)

    def test_missing_book_rejected(self):
        prepared = requests(self.sample(), mode="NCE")
        with self.assertRaises(ValueError):
            staging_http_jobs(prepared, textbook_id="",
                              item_id_factory=lambda: str(uuid4()))

    def test_duplicate_item_id_rejected(self):
        prepared = requests(self.sample(count=2), mode="NCE")
        fixed = str(uuid4())
        with self.assertRaisesRegex(ValueError, "Duplicate item ID"):
            staging_http_jobs(prepared, textbook_id="t1",
                              item_id_factory=lambda: fixed)

    def test_tampered_topic_rejected(self):
        prepared = requests(self.sample(), mode="NCE")
        prepared["requests"][0]["topic"] = "changed"
        with self.assertRaisesRegex(ValueError, "topic mismatch"):
            staging_http_jobs(prepared, textbook_id="t1",
                              item_id_factory=lambda: str(uuid4()))

    def test_paid_execution_requires_explicit_flag(self):
        prepared = requests(self.sample(), mode="NCE")
        result = staging_http_jobs(prepared, textbook_id="t1",
                                   item_id_factory=lambda: str(uuid4()), execute=True)
        self.assertEqual(result["jobs"][0]["path"], "/generation/one")
        self.assertTrue(result["jobs"][0]["body"]["confirm_paid_calls"])
        self.assertFalse(result["auto_publish"])
