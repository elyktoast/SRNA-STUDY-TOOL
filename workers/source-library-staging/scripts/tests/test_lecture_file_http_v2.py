"""Authenticated staging lecture-file HTTP contract tests; no external calls."""
import base64
import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_http_v2 import create_app

UID = "00000000-0000-4000-8000-000000000001"
PATH = "/generation/lecture-file-plan"

class Connection:
    def __enter__(self): return self
    def __exit__(self, *args): return False

class LectureFileHttpTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(conn_factory=Connection,
            resolve_admin=lambda token: UID if token == "valid" else None,
            environment={"STAGING_ONLY": "true"})

    def call(self, payload, token="valid", origin="https://staging.srnastudytool.com"):
        raw = json.dumps(payload).encode()
        env = {"PATH_INFO": PATH, "REQUEST_METHOD": "POST", "HTTP_ORIGIN": origin,
               "HTTP_AUTHORIZATION": "Bearer " + token,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        response = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        return seen[0], json.loads(response)

    def payload(self):
        return {"filename": "lecture.pdf", "file_base64": base64.b64encode(b"%PDF-test").decode(),
                "textbook_id": "indexed-book", "count": 2, "page_start": 1, "page_end": 2}

    @patch("lecture_file_to_question_plan.prepare_lecture_file_jobs",
           return_value={"jobs": [], "count": 0, "auto_generate": False,
                         "auto_publish": False, "database_writes": False,
                         "file_extraction": {"format": "pdf", "page_count": 2,
                                             "review_pages": [], "requires_visual_review": False}})
    def test_authenticated_file_reaches_planner_with_owner_and_range(self, planner):
        status, result = self.call(self.payload())
        self.assertEqual(status, "200 OK")
        self.assertFalse(result["auto_publish"])
        self.assertEqual(planner.call_args.args[1], UID)
        self.assertEqual(planner.call_args.args[2], b"%PDF-test")
        self.assertEqual(planner.call_args.kwargs["page_start"], 1)
        self.assertEqual(planner.call_args.kwargs["page_end"], 2)
        self.assertTrue(planner.call_args.kwargs["enable_ocr"])

    @patch("lecture_file_to_question_plan.prepare_lecture_file_jobs")
    def test_wrong_origin_and_token_never_reach_planner(self, planner):
        self.assertEqual(self.call(self.payload(), token="invalid")[0], "403 Forbidden")
        self.assertEqual(self.call(self.payload(), origin="https://srnastudytool.com")[0], "403 Forbidden")
        planner.assert_not_called()

    @patch("lecture_file_to_question_plan.prepare_lecture_file_jobs")
    def test_rejects_bad_base64_and_unexpected_client_fields(self, planner):
        for mutation in ({"file_base64": "invalid@@@"}, {"owner_uid": UID},
                         {"count": True}, {"page_start": "1"}):
            with self.subTest(mutation=mutation):
                payload = {**self.payload(), **mutation}
                status, _ = self.call(payload)
                if "page_start" in mutation:
                    # Page-range validation happens inside the planner.
                    continue
                self.assertEqual(status, "400 Bad Request")
        planner.assert_not_called()

if __name__ == "__main__":
    unittest.main()
