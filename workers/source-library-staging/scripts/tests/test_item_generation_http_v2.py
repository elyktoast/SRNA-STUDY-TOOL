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
           "section": "III.H", "objective": "III.H.4", "item_id": "draft-1"}

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

if __name__ == "__main__":
    unittest.main()
