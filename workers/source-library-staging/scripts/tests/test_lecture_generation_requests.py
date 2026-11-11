import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lecture_generation_requests import requests, staging_http_jobs
from lecture_to_question_plan import prepare_staging_jobs
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
        self.assertEqual(result["requests"][0]["concept_request"]["section"], "H")
        self.assertEqual(result["requests"][0]["concept_request"]["format"], "MC")
    def test_invalid_format_rejected(self):
        with self.assertRaisesRegex(ValueError, "format"):
            requests({"topics": []}, mode="NCE", format="INVALID")

    def test_missing_evidence_rejected(self):
        p = {"topics": [{"title": "Unsupported", "question_count": 1, "evidence": []}]}
        with self.assertRaises(ValueError):
            requests(p, mode="NCE", domain="III",
                     section="III.H", objective="III.H.4")

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
        self.assertNotIn("execute", jobs["jobs"][0]["body"])
        self.assertNotIn("confirm_paid_calls", jobs["jobs"][0]["body"])

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

    def test_unrelated_textbook_rejected(self):
        prepared = requests(self.sample(), mode="NCE")
        with self.assertRaisesRegex(ValueError, "Selected textbook"):
            staging_http_jobs(prepared, textbook_id="different-book",
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

    def test_composed_lecture_preflight_only(self):
        prepared_plan = self.sample()
        prepared_plan.update({"requested": 1, "planned": 1,
                              "coverage": {"lecture_concepts": 1, "grounded_concepts": 1,
                                           "uncovered_concepts": 0},
                              "missing_textbook_support": [],
                              "extraction": {"method": "headings", "requires_review": True}})
        with patch("lecture_to_question_plan.prepare", return_value=prepared_plan) as mock_prepare:
            result = prepare_staging_jobs(object(), "owner", "lecture text",
                                          textbook_id="t1",
                                          item_id_factory=lambda: str(uuid4()),
                                          count=1)
        mock_prepare.assert_called_once()
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["jobs"][0]["path"], "/generation/preflight")
        self.assertFalse(result["auto_generate"])
        self.assertFalse(result["database_writes"])
        self.assertNotIn("evidence", result["lecture_plan"]["topics"][0])
        self.assertNotIn("Grounded textbook evidence", str(result["lecture_plan"]))
        self.assertEqual(result["lecture_plan"]["planned"], 1)

    def test_composed_lecture_requires_book(self):
        with self.assertRaisesRegex(ValueError, "textbook"):
            prepare_staging_jobs(object(), "owner", "lecture",
                                 textbook_id="", item_id_factory=lambda: str(uuid4()))

    def test_paid_execution_requires_explicit_flag(self):
        prepared = requests(self.sample(), mode="NCE")
        result = staging_http_jobs(prepared, textbook_id="t1",
                                   item_id_factory=lambda: str(uuid4()), execute=True)
        self.assertEqual(result["jobs"][0]["path"], "/generation/one")
        self.assertNotIn("confirm_paid_calls", result["jobs"][0]["body"])
        self.assertNotIn("execute", result["jobs"][0]["body"])
        self.assertFalse(result["auto_publish"])


if __name__ == "__main__":
    unittest.main()
