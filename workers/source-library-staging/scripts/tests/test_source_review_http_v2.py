"""HTTP boundary tests: auth before R2, owner binding, verified PNG, no approvals."""
import hashlib
import io
import unittest
from unittest.mock import patch

from source_review_http_v2 import create_app
from source_review_runtime_v2 import StagingReviewRuntime

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/test.pdf"


class Auth:
    def get_user(self, token):
        if token != "valid":
            raise ValueError("Invalid token")
        return {"id": UID, "active": True}


class Roles:
    def is_active_admin(self, uid):
        return uid == UID


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.runtime = StagingReviewRuntime(
            conn=object(), r2_client=object(), supabase_url="unused",
            supabase_api_key="unused", signing_secret="x" * 64,
            auth_provider=Auth(), role_store=Roles())
        self.app = create_app(self.runtime)
        self.manifest = {"owner_uid": UID, "r2_key": KEY,
                         "sha256": "a" * 64, "pdf_page_count": 2}

    def call(self, path="/review/page.png", query=None, token="valid", method="GET"):
        headers = []
        status = []
        def start(s, h):
            status.append(s)
            headers.extend(h)
        env = {"REQUEST_METHOD": method, "PATH_INFO": path,
               "QUERY_STRING": query if query is not None else "path=" + KEY + "&page=1"}
        if token is not None:
            env["HTTP_AUTHORIZATION"] = "Bearer " + token
        body = b"".join(self.app(env, start))
        return int(status[0].split()[0]), dict(headers), body

    def test_health_is_read_only(self):
        status, headers, body = self.call("/health", token=None)
        self.assertEqual(status, 200)
        self.assertIn(b'"approval_enabled":false', body)
        self.assertEqual(headers["X-Review-Approval-Enabled"], "false")

    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_authentication_precedes_storage(self, loader):
        for token in (None, "invalid", " "):
            status, _, _ = self.call(token=token)
            self.assertIn(status, (400, 401, 403))
        loader.assert_not_called()

    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_duplicate_and_unexpected_query_fields_denied(self, loader):
        for query in ("path=" + KEY + "&page=1&page=2",
                      "path=" + KEY + "&page=1&approved=true",
                      "path=" + KEY + "&page=NaN"):
            self.assertEqual(self.call(query=query)[0], 400)
        loader.assert_not_called()

    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_foreign_owner_cannot_select_manifest_owner(self, loader):
        loader.side_effect = ValueError("Invalid owner-scoped PDF key")
        status, _, _ = self.call(query="path=00000000-0000-4000-8000-000000000000/other.pdf&page=1")
        self.assertEqual(status, 409)
        loader.assert_called_once()
        self.assertEqual(loader.call_args.kwargs["owner_uid"], UID)

    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_manifest_returns_only_verified_public_fields(self, loader):
        loader.return_value = self.manifest
        status, headers, body = self.call("/review/manifest", query="path=" + KEY)
        self.assertEqual(status, 200)
        self.assertNotIn(b"owner_uid", body)
        self.assertIn(b'"pdf_page_count":2', body)
        self.assertEqual(headers["X-Review-Approval-Enabled"], "false")

    @patch("source_review_http_v2.load_verified_review_page")
    @patch("source_review_http_v2.fetch_verified_staging_pdf")
    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_image_is_verified_and_never_issues_receipt(self, manifest, fetch, render):
        manifest.return_value = self.manifest
        fetch.return_value = b"%PDF-fixture"
        png = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"fixture"
        render.return_value = {"png": png, "image_sha256": hashlib.sha256(png).hexdigest(),
                               "source_sha256": "a" * 64}
        status, headers, body = self.call()
        self.assertEqual(status, 200)
        self.assertEqual(body, png)
        self.assertEqual(headers["Content-Type"], "image/png")
        self.assertEqual(headers["X-Review-Approval-Enabled"], "false")
        self.assertNotIn("X-Inspection-Receipt", headers)
        self.assertEqual(headers["X-Page-Image-SHA256"], hashlib.sha256(png).hexdigest())
        fetch.assert_called_once()
        render.assert_called_once()

    @patch("source_review_http_v2.fetch_verified_staging_pdf")
    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_out_of_range_page_rejected_before_pdf_download(self, manifest, fetch):
        manifest.return_value = self.manifest
        status, _, _ = self.call(query="path=" + KEY + "&page=3")
        self.assertEqual(status, 409)
        fetch.assert_not_called()

    @patch("source_review_http_v2.load_staging_review_manifest", side_effect=ValueError("tampered"))
    def test_attestation_failure_is_conflict(self, loader):
        self.assertEqual(self.call()[0], 409)

    @patch("source_review_http_v2.load_verified_review_page")
    @patch("source_review_http_v2.fetch_verified_staging_pdf", return_value=b"%PDF")
    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_image_or_source_digest_mismatch_never_served(self, manifest, fetch, render):
        manifest.return_value = self.manifest
        png = bytes([137, 80, 78, 71, 13, 10, 26, 10]) + b"fixture"
        cases = (
            {"png": png, "image_sha256": "0" * 64, "source_sha256": "a" * 64},
            {"png": png, "image_sha256": hashlib.sha256(png).hexdigest(), "source_sha256": "b" * 64},
            {"png": b"not-a-png", "image_sha256": hashlib.sha256(b"not-a-png").hexdigest(), "source_sha256": "a" * 64},
        )
        for page in cases:
            with self.subTest(page=page):
                render.return_value = page
                status, headers, body = self.call()
                self.assertEqual(status, 409)
                self.assertNotEqual(headers["Content-Type"], "image/png")
                self.assertNotIn("X-Inspection-Receipt", headers)

    @patch("source_review_http_v2.load_verified_review_page")
    @patch("source_review_http_v2.fetch_verified_staging_pdf", return_value=b"%PDF")
    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_page_renderer_failure_never_returns_unverified_bytes(self, manifest, fetch, render):
        manifest.return_value = self.manifest
        render.side_effect = RuntimeError("renderer unavailable")
        status, headers, body = self.call()
        self.assertEqual(status, 503)
        self.assertEqual(headers["Cache-Control"], "private, no-store")
        self.assertNotIn("X-Page-Image-SHA256", headers)
        self.assertNotIn("X-Inspection-Receipt", headers)

    def test_approval_routes_are_not_exposed(self):
        self.assertEqual(self.call("/review/approve", method="POST")[0], 405)
        self.assertEqual(self.call("/review/approve")[0], 404)


if __name__ == "__main__":
    unittest.main()
