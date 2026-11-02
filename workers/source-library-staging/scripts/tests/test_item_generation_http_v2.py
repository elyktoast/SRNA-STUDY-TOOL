import io
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_http_v2 import create_app

UID = "00000000-0000-4000-8000-000000000001"
PAYLOAD = {"topic": "airway", "mode": "NCE", "domain": "III",
           "section": "H", "objective": "III.H.4", "item_id": "draft-1"}

class Connection:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False

class HttpPreflightTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(conn_factory=Connection, resolve_admin=lambda token: UID if token == "valid" else None,
                              environment={"STAGING_ONLY": "true"})

    def call(self, payload=PAYLOAD, token="valid", origin="https://staging.srnastudytool.com"):
        raw = json.dumps(payload).encode()
        env = {"PATH_INFO": "/generation/preflight", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": origin, "HTTP_AUTHORIZATION": "Bearer " + token,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        body = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        return seen[0], json.loads(body)

    @patch("item_generation_http_v2.execute", return_value={"dry_run": True, "passage_count": 2, "can_publish": False, "database_writes": False})
    def test_admin_preflight_only(self, execute):
        status, data = self.call()
        self.assertEqual(status, "200 OK")
        self.assertTrue(data["dry_run"])
        self.assertFalse(execute.call_args.args[1].execute)
        self.assertEqual(execute.call_args.args[1].owner_uid, UID)

    @patch("item_generation_http_v2.execute", return_value={"dry_run": False, "item": {"stem": "Sample"}, "can_publish": False, "database_writes": False})
    def test_single_question_requires_server_opt_in(self, execute):
        raw = json.dumps({**PAYLOAD, "textbook_id": "00000000-0000-4000-8000-000000000002"}).encode()
        env = {"PATH_INFO": "/generation/one", "REQUEST_METHOD": "POST",
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer valid",
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        body = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        self.assertEqual(seen[0], "403 Forbidden")
        execute.assert_not_called()
        enabled = create_app(conn_factory=Connection, resolve_admin=lambda token: UID if token == "valid" else None,
                             environment={"STAGING_ONLY": "true", "AI_GENERATION_OPT_IN": "true"})
        seen.clear()
        body = b"".join(enabled({**env, "wsgi.input": io.BytesIO(raw)}, lambda status, headers: seen.append(status)))
        self.assertEqual(seen[0], "200 OK")
        self.assertEqual(json.loads(body)["item"]["stem"], "Sample")
        self.assertTrue(execute.call_args.args[1].execute)
        self.assertTrue(execute.call_args.args[1].confirm_paid_calls)

    @patch("item_generation_http_v2.execute")
    def test_no_model_execution_from_http(self, execute):
        status, _ = self.call({**PAYLOAD, "execute": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_unauthorized_rejected_before_database(self, execute):
        status, _ = self.call(token="invalid")
        self.assertEqual(status, "403 Forbidden")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_other_origin_rejected(self, execute):
        status, _ = self.call(origin="https://srnastudytool.com")
        self.assertEqual(status, "403 Forbidden")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_paid_confirmation_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "confirm_paid_calls": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_invalid_blueprint_rejected_before_database(self, execute):
        for change in ({"section": "III.H"}, {"objective": "II.H.4"},
                       {"domain": "V"}, {"format": "TF"}):
            with self.subTest(change=change):
                status, _ = self.call({**PAYLOAD, **change})
                self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_boolean_limit_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "limit": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_duplicate_unknown_field_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "admin_override": True})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

    @patch("item_generation_http_v2.execute")
    def test_invalid_range_rejected(self, execute):
        status, _ = self.call({**PAYLOAD, "page_start": 9, "page_end": 2})
        self.assertEqual(status, "400 Bad Request")
        execute.assert_not_called()

class DraftBasketHttpTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(conn_factory=Connection,
            resolve_admin=lambda token: UID if token == "valid" else None,
            environment={"STAGING_ONLY": "true"})

    def call(self, path, method="GET", payload=None, token="valid"):
        raw = json.dumps(payload).encode() if payload is not None else b""
        env = {"PATH_INFO": path, "REQUEST_METHOD": method,
               "HTTP_ORIGIN": "https://staging.srnastudytool.com",
               "HTTP_AUTHORIZATION": "Bearer " + token,
               "CONTENT_LENGTH": str(len(raw)), "wsgi.input": io.BytesIO(raw)}
        seen = []
        body = b"".join(self.app(env, lambda status, headers: seen.append(status)))
        return seen[0], json.loads(body) if body else {}

    @patch("item_generation_http_v2.list_drafts", return_value=[])
    def test_list_requires_admin(self, mock_list):
        status, data = self.call("/generation/drafts")
        self.assertEqual(status, "200 OK")
        self.assertEqual(data["drafts"], [])
        self.assertEqual(mock_list.call_args.kwargs["owner_uid"], UID)
        status, _ = self.call("/generation/drafts", token="invalid")
        self.assertEqual(status, "403 Forbidden")
        self.assertEqual(mock_list.call_count, 1)

    @patch("item_generation_http_v2.save", return_value={"status": "pending_review"})
    def test_save_uses_verified_owner(self, mock_save):
        status, data = self.call("/generation/drafts", "POST", {"topic": "airway"})
        self.assertEqual(status, "201 Created")
        self.assertEqual(mock_save.call_args.args[1]["owner_uid"], UID)
        self.assertEqual(data["status"], "pending_review")
        status, _ = self.call("/generation/drafts", "POST", {"owner_uid": UID})
        self.assertEqual(status, "422 Unprocessable Entity")
        self.assertEqual(mock_save.call_count, 1)

    @patch("item_generation_http_v2.get_draft", return_value={"published": False})
    def test_detail_scoped_to_owner(self, mock_get):
        draft_id = "00000000-0000-4000-8000-000000000002"
        status, data = self.call("/generation/drafts/" + draft_id)
        self.assertEqual(status, "200 OK")
        self.assertEqual(mock_get.call_args.kwargs["owner_uid"], UID)
        self.assertFalse(data["published"])

    @patch("item_generation_http_v2.review", return_value={"published": False})
    def test_review_uses_verified_reviewer(self, mock_review):
        draft_id = "00000000-0000-4000-8000-000000000002"
        status, _ = self.call("/generation/drafts/" + draft_id + "/review",
                              "POST", {"status": "rejected", "notes": "Unsupported"})
        self.assertEqual(status, "200 OK")
        self.assertEqual(mock_review.call_args.kwargs["reviewer_uid"], UID)
        self.assertEqual(mock_review.call_args.kwargs["owner_uid"], UID)

if __name__ == "__main__":
    unittest.main()
