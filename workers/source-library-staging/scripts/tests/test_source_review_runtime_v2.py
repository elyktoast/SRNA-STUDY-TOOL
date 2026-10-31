"""Tests for trusted staging reviewer runtime composition."""
import unittest
from unittest.mock import patch
from source_review_runtime_v2 import StagingReviewRuntime

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
KEY = UID + "/fixture.pdf"
MANIFEST = {"owner_uid": UID, "r2_key": KEY, "sha256": "a" * 64, "pdf_page_count": 2}


class Auth:
    def get_user(self, token):
        if token != "valid":
            raise ValueError("Invalid session")
        return {"id": UID, "active": True}


class Roles:
    def is_active_admin(self, uid):
        return uid == UID


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.conn = object()
        self.r2 = object()
        self.runtime = StagingReviewRuntime(
            conn=self.conn, r2_client=self.r2, supabase_url="unused",
            supabase_api_key="unused", signing_secret="s" * 64,
            auth_provider=Auth(), role_store=Roles())

    def test_requires_privileged_adapters(self):
        with self.assertRaisesRegex(ValueError, "connections"):
            StagingReviewRuntime(conn=None, r2_client=self.r2, supabase_url="",
                                 supabase_api_key="", signing_secret="s" * 64)
        with self.assertRaisesRegex(ValueError, "signing secret"):
            StagingReviewRuntime(conn=self.conn, r2_client=self.r2,
                                 supabase_url="", supabase_api_key="",
                                 signing_secret="weak")

    @patch("source_review_runtime_v2.load_staging_review_manifest", return_value=MANIFEST)
    def test_manifest_requires_verified_admin(self, load):
        with self.assertRaisesRegex(ValueError, "Invalid session"):
            self.runtime.manifest(token="invalid", r2_key=KEY)
        load.assert_not_called()
        self.assertEqual(self.runtime.manifest(token="valid", r2_key=KEY), MANIFEST)
        load.assert_called_once_with(self.r2, owner_uid=UID, r2_key=KEY)

    @patch("source_review_runtime_v2.inspect_and_register_page")
    @patch("source_review_runtime_v2.load_staging_review_manifest", return_value=MANIFEST)
    @patch("source_review_runtime_v2.fetch_verified_staging_pdf", return_value=b"%PDF-test")
    def test_inspection_wires_attested_manifest_and_original_source(self, fetch, manifest, inspect):
        inspect.side_effect = lambda **kwargs: (
            kwargs["manifest_loader"](UID, KEY),
            kwargs["source_loader"](UID, KEY))
        output = self.runtime.inspect(token="valid", r2_key=KEY,
                                      pdf_page=1, write_image=lambda **kw: 1)
        self.assertEqual(output, (MANIFEST, b"%PDF-test"))
        self.assertEqual(manifest.call_count, 2)
        fetch.assert_called_once_with(self.r2, owner_uid=UID, r2_key=KEY,
                                      expected_sha256=MANIFEST["sha256"])

    @patch("source_review_runtime_v2.approve_inspected_page", return_value=1)
    @patch("source_review_runtime_v2.load_staging_review_manifest", return_value=MANIFEST)
    @patch("source_review_runtime_v2.fetch_verified_staging_pdf", return_value=b"%PDF-test")
    def test_approval_rechecks_original_source_before_nonce_consumption(self, fetch, manifest, approve):
        self.assertEqual(self.runtime.approve(token="valid", r2_key=KEY, pdf_page=1,
                         review_note="inspected", receipt="receipt", image_sha256="b" * 64), 1)
        fetch.assert_called_once()
        approve.assert_called_once()

    @patch("source_review_runtime_v2.approve_inspected_page")
    @patch("source_review_runtime_v2.load_staging_review_manifest", return_value=MANIFEST)
    @patch("source_review_runtime_v2.fetch_verified_staging_pdf", side_effect=ValueError("Source changed"))
    def test_changed_source_blocks_approval_before_nonce(self, fetch, manifest, approve):
        with self.assertRaisesRegex(ValueError, "Source changed"):
            self.runtime.approve(token="valid", r2_key=KEY, pdf_page=1,
                                 review_note="inspected", receipt="receipt", image_sha256="b" * 64)
        approve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
