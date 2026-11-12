"""Adapter tests: never write without trusted source/image and receipt validation."""
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from source_review_approval_request_service_v2 import approve_verified_request

UID = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
KEY = UID + "/1878c3ce-7202-4569-82a0-5029d77b2054.pdf"
MANIFEST = {"owner_uid": UID, "r2_key": KEY, "sha256": "a" * 64,
            "pdf_page_count": 3011}
REQUEST = {"path": KEY, "page": 2882, "source_sha256": "a" * 64,
           "image_sha256": "b" * 64, "receipt": "synthetic-receipt",
           "classification": "non_content_divider",
           "review_note": "Manually inspected section index divider"}


class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.runtime = SimpleNamespace(
            auth=object(), roles=object(), r2=object(), conn=object(),
            secret=b"synthetic-secret-32-bytes-minimum!!",
            manifest=lambda **kwargs: dict(MANIFEST))

    def call(self, value=None):
        return approve_verified_request(
            self.runtime, access_token="valid",
            body=json.dumps(REQUEST if value is None else value).encode())

    @patch("source_review_approval_request_service_v2.approve_inspected_page", return_value=1)
    @patch("source_review_approval_request_service_v2.load_verified_review_page")
    @patch("source_review_approval_request_service_v2.resolve_admin_reviewer")
    def test_validated_request_preserves_classification(self, reviewer, page, approve):
        reviewer.return_value = SimpleNamespace(uid=UID)
        page.return_value = {"image_sha256": "b" * 64}
        self.assertEqual(self.call(), 1)
        self.assertEqual(approve.call_args.kwargs["pdf_page"], 2882)
        self.assertEqual(approve.call_args.kwargs["image_sha256"], "b" * 64)
        self.assertEqual(approve.call_args.kwargs["review_note"],
                         "[non_content_divider] Manually inspected section index divider")

    @patch("source_review_approval_request_service_v2.approve_inspected_page")
    @patch("source_review_approval_request_service_v2.load_verified_review_page")
    @patch("source_review_approval_request_service_v2.resolve_admin_reviewer")
    def test_rejects_unverified_source_and_page_without_writing(self, reviewer, page, approve):
        reviewer.return_value = SimpleNamespace(uid=UID)
        page.return_value = {"image_sha256": "b" * 64}
        cases = [
            {**REQUEST, "source_sha256": "c" * 64},
            {**REQUEST, "image_sha256": "c" * 64},
            {**REQUEST, "page": 3012},
            {**REQUEST, "path": UID + "/other.pdf"},
        ]
        for request in cases:
            with self.subTest(request=request), self.assertRaises(ValueError):
                self.call(request)
        approve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
