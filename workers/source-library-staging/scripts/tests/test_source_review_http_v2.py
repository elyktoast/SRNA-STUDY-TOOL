"""HTTP boundary tests: auth before R2, owner binding, verified PNG, no approvals."""
import hashlib
import json
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

    def call(self, path="/review/page.png", query=None, token="valid", method="GET", origin=None, preflight_method=None, preflight_headers="Authorization"):
        headers = []
        status = []
        def start(s, h):
            status.append(s)
            headers.extend(h)
        env = {"REQUEST_METHOD": method, "PATH_INFO": path,
               "QUERY_STRING": query if query is not None else "path=" + KEY + "&page=1"}
        if origin is not None:
            env["HTTP_ORIGIN"] = origin
        if preflight_method is not None:
            env["HTTP_ACCESS_CONTROL_REQUEST_METHOD"] = preflight_method
        if method == "OPTIONS" and preflight_headers is not None:
            env["HTTP_ACCESS_CONTROL_REQUEST_HEADERS"] = preflight_headers
        if token is not None:
            env["HTTP_AUTHORIZATION"] = "Bearer " + token
        body = b"".join(self.app(env, start))
        return int(status[0].split()[0]), dict(headers), body

    def test_security_headers_on_all_read_only_responses(self):
        for path, method in (("/health", "GET"), ("/review/approve", "POST"),
                             ("/missing", "GET")):
            with self.subTest(path=path, method=method):
                status, headers, _ = self.call(path, method=method, token=None)
                self.assertIn(status, (200, 404, 405))
                self.assertEqual(headers["X-Frame-Options"], "DENY")
                self.assertEqual(headers["Referrer-Policy"], "no-referrer")
                self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
                self.assertEqual(headers["X-Review-Approval-Enabled"], "false")
                self.assertEqual(headers["Cache-Control"], "private, no-store")

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
        self.assertEqual(headers["X-Verified-Source-SHA256"], "a" * 64)
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

    @patch("source_review_http_v2.fetch_verified_staging_pdf")
    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_mismatched_manifest_identity_fails_before_source_fetch(self, manifest, fetch):
        for changed in (
            {"owner_uid": "00000000-0000-4000-8000-000000000000"},
            {"r2_key": UID + "/different.pdf"},
            {"pdf_page_count": 0},
            {"sha256": "bad"},
        ):
            with self.subTest(changed=changed):
                manifest.return_value = {**self.manifest, **changed}
                self.assertEqual(self.call()[0], 409)
                self.assertEqual(self.call("/review/manifest", query="path=" + KEY)[0], 409)
        fetch.assert_not_called()

    def test_staging_origin_preflight_is_strict_and_has_no_receipt(self):
        status, headers, body = self.call(method="OPTIONS", token=None,
            origin="https://staging.srnastudytool.com", preflight_method="GET")
        self.assertEqual(status, 204)
        self.assertEqual(body, b"")
        self.assertEqual(headers["Access-Control-Allow-Origin"], "https://staging.srnastudytool.com")
        self.assertEqual(headers["Access-Control-Allow-Headers"], "Authorization")
        self.assertEqual(headers["X-Review-Approval-Enabled"], "false")
        self.assertNotIn("X-Inspection-Receipt", headers)

    def test_preflight_rejects_unapproved_routes_and_headers(self):
        for path, headers in (("/health", "Authorization"),
                              ("/review/approve", "Authorization"),
                              ("/review/manifest", "Authorization, X-Admin"),
                              ("/review/page.png", ""),
                              ("/review/page.png", "X-Receipt")):
            with self.subTest(path=path, headers=headers):
                status, response_headers, _ = self.call(path, method="OPTIONS",
                    token=None, origin="https://staging.srnastudytool.com",
                    preflight_method="GET", preflight_headers=headers)
                self.assertEqual(status, 403)
                self.assertNotIn("X-Inspection-Receipt", response_headers)

    def test_other_origins_and_unsafe_preflights_are_denied(self):
        for origin, method in (
            ("https://srnastudytool.com", "GET"),
            ("https://staging.srnastudytool.com.evil.test", "GET"),
            ("null", "GET"),
            ("https://staging.srnastudytool.com", "POST"),
            ("https://staging.srnastudytool.com", None),
        ):
            with self.subTest(origin=origin, method=method):
                status, headers, _ = self.call(method="OPTIONS", token=None,
                    origin=origin, preflight_method=method)
                self.assertEqual(status, 403)
                if origin != "https://staging.srnastudytool.com":
                    self.assertNotIn("Access-Control-Allow-Origin", headers)
                self.assertNotIn("X-Inspection-Receipt", headers)

    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_disallowed_origin_rejected_before_storage_access(self, loader):
        status, headers, _ = self.call(origin="https://srnastudytool.com")
        self.assertEqual(status, 403)
        self.assertNotIn("Access-Control-Allow-Origin", headers)
        loader.assert_not_called()

    @patch("source_review_http_v2.load_staging_review_manifest")
    def test_staging_origin_can_read_manifest_and_verification_headers(self, loader):
        loader.return_value = self.manifest
        status, headers, _ = self.call("/review/manifest", query="path=" + KEY,
            origin="https://staging.srnastudytool.com")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Access-Control-Allow-Origin"], "https://staging.srnastudytool.com")
        self.assertIn("X-Verified-Source-SHA256", headers["Access-Control-Expose-Headers"])
        self.assertIn("X-Review-Approval-Enabled", headers["Access-Control-Expose-Headers"])
        self.assertEqual(headers["Vary"], "Origin")

    def test_real_pdf_render_via_verified_r2_adapters(self):
        import fitz
        from unittest.mock import patch
        document = fitz.open()
        page = document.new_page(width=300, height=400)
        page.insert_text((40, 50), "Staging verified textbook page")
        pdf = document.tobytes()
        document.close()
        sha = hashlib.sha256(pdf).hexdigest()
        queue_key = UID + "/_review_queues/test.pdf.json"
        queue = json.dumps({"r2_key": KEY, "source_sha256": sha,
                            "approval_enabled": False, "pdf_page_count": 1,
                            "pages": []}).encode()
        queue_sha = hashlib.sha256(queue).hexdigest()
        att = json.dumps({"schema_version": 1, "r2_key": KEY,
                          "source_sha256": sha, "queue_sha256": queue_sha,
                          "source_etag": '"fixture-etag"', "size_bytes": len(pdf)}).encode()

        class Stream:
            def __init__(self, content):
                self.content = content
            def read(self, n=-1):
                return self.content[:n]
            def iter_chunks(self, chunk_size):
                for offset in range(0, len(self.content), chunk_size):
                    yield self.content[offset:offset + chunk_size]
            def close(self):
                pass

        class R2:
            def head_object(self, *, Bucket, Key):
                self_key = KEY
                if Bucket != "srna-staging-textbooks" or Key != self_key:
                    raise ValueError("Unexpected storage key")
                return {"ETag": '"fixture-etag"', "ContentLength": len(pdf)}
            def get_object(self, *, Bucket, Key):
                if Bucket != "srna-staging-textbooks":
                    raise ValueError("Wrong bucket")
                value = {KEY: pdf, queue_key: queue,
                         queue_key + ".source.json": att}[Key]
                return {"Body": Stream(value), "ContentLength": len(value),
                        "ETag": '"fixture-etag"'}

        self.runtime.r2 = R2()
        status, headers, body = self.call()
        self.assertEqual(status, 200)
        self.assertTrue(body.startswith(bytes([137, 80, 78, 71, 13, 10, 26, 10])))
        self.assertEqual(headers["X-Verified-Source-SHA256"], sha)
        self.assertEqual(headers["X-Page-Image-SHA256"], hashlib.sha256(body).hexdigest())
        self.assertNotIn("X-Inspection-Receipt", headers)
        status, _, _ = self.call(query="path=" + KEY + "&page=2")
        self.assertEqual(status, 409)

    def test_approval_routes_are_not_exposed(self):
        self.assertEqual(self.call("/review/approve", method="POST")[0], 405)
        self.assertEqual(self.call("/review/approve")[0], 404)


if __name__ == "__main__":
    unittest.main()
