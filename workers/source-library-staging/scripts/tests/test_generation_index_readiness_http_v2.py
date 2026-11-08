"""No network or database required: staging readiness API boundary tests."""
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_http_v2 import create_app

UID = "00000000-0000-4000-8000-000000000001"
PATH = "/generation/index-readiness"


def call(app, method="GET", token="valid", origin="https://staging.srnastudytool.com"):
    env = {"PATH_INFO": PATH, "REQUEST_METHOD": method, "HTTP_ORIGIN": origin,
           "HTTP_AUTHORIZATION": "Bearer " + token}
    seen = []
    result = b"".join(app(env, lambda status, headers: seen.append(status)))
    return seen[0], json.loads(result)


class ReadinessHttpTests(unittest.TestCase):
    def make_app(self, factory=None):
        return create_app(conn_factory=lambda: None,
                          resolve_admin=lambda token: UID if token == "valid" else None,
                          environment={"STAGING_ONLY": "true"},
                          readiness_factory=factory)

    def test_ready_read_only_and_owner_scoped(self):
        owners = []
        app = self.make_app(lambda owner: (owners.append(owner) or {
            "ready": True, "inventory_digest": "a" * 64, "expected_count": 9000, "indexed_count": 9000,
            "missing_count": 0, "unexpected_count": 0, "stale_count": 0}))
        status, data = call(app)
        self.assertEqual(status, "200 OK")
        self.assertTrue(data["ready"])
        self.assertEqual(owners, [UID])

    def test_missing_factory_fails_closed(self):
        status, data = call(self.make_app())
        self.assertEqual(status, "503 Service Unavailable")
        self.assertFalse(data["ready"])

    def test_backend_failure_does_not_leak_details(self):
        def broken(_):
            raise RuntimeError("private database credential")
        status, data = call(self.make_app(broken))
        self.assertEqual(status, "503 Service Unavailable")
        self.assertNotIn("credential", json.dumps(data))

    def test_sensitive_or_inconsistent_result_rejected(self):
        for result in (
            {"ready": True, "inventory_digest": "a" * 64,
             "expected_count": 1, "indexed_count": 0,
             "missing_count": 1, "unexpected_count": 0, "stale_count": 0},
            {"ready": True, "inventory_digest": "a" * 64,
             "expected_count": 1, "indexed_count": 1,
             "missing_count": 0, "unexpected_count": 0, "stale_count": 0,
             "question_ids": ["private"]},
        ):
            with self.subTest(result=result):
                status, data = call(self.make_app(lambda _: result))
                self.assertEqual(status, "503 Service Unavailable")
                self.assertNotIn("question_ids", data)

    def test_invalid_response_fails_closed(self):
        status, data = call(self.make_app(lambda _: {"ready": "yes"}))
        self.assertEqual(status, "503 Service Unavailable")
        self.assertFalse(data["ready"])

    def test_auth_origin_and_method_enforced_before_factory(self):
        owners = []
        app = self.make_app(lambda owner: owners.append(owner))
        self.assertEqual(call(app, token="invalid")[0], "403 Forbidden")
        self.assertEqual(call(app, origin="https://srnastudytool.com")[0], "403 Forbidden")
        self.assertEqual(call(app, method="POST")[0], "405 Method Not Allowed")
        self.assertEqual(owners, [])


if __name__ == "__main__":
    unittest.main()
