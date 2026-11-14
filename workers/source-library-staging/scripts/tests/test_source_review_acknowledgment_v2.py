import unittest
from types import SimpleNamespace
from unittest.mock import patch
from contextlib import nullcontext

from source_review_delivery_challenge_v2 import issue_delivery_challenge
from source_review_receipt_service_v2 import register_acknowledged_page_receipt

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
PAGE = {"owner_uid": UID, "r2_key": UID + "/book.pdf",
        "source_sha256": "a" * 64, "image_sha256": "b" * 64, "pdf_page": 7}
SECRET = b"strong-staging-secret-not-for-production-123"


class FakeConn:
    def transaction(self):
        return nullcontext()


class AcknowledgmentTests(unittest.TestCase):
    def setUp(self):
        self.challenge = issue_delivery_challenge(
            SECRET, reviewer_uid=UID, page=PAGE, now=100)

    def call(self, **changes):
        values = dict(conn=FakeConn(), page=PAGE, access_token="valid",
                      auth_provider=object(), protected_role_store=object(),
                      signing_secret=SECRET, delivery_challenge=self.challenge,
                      acknowledged=True, now=100)
        return register_acknowledged_page_receipt(**{**values, **changes})

    @patch("source_review_receipt_service_v2.consume_inspection_nonce")
    @patch("source_review_receipt_service_v2.register_delivered_page_receipt",
           return_value="signed-receipt")
    @patch("source_review_receipt_service_v2.resolve_admin_reviewer")
    def test_explicit_acknowledgment_registers_receipt(self, reviewer, register, consume):
        reviewer.return_value = SimpleNamespace(uid=UID)
        self.assertEqual(self.call(), "signed-receipt")
        self.assertEqual(register.call_args.kwargs["delivered_image_sha256"], "b" * 64)
        consume.assert_called_once()

    @patch("source_review_receipt_service_v2.consume_inspection_nonce")
    @patch("source_review_receipt_service_v2.register_delivered_page_receipt")
    @patch("source_review_receipt_service_v2.resolve_admin_reviewer")
    def test_no_receipt_for_unacknowledged_stale_or_mismatched_page(self, reviewer, register, consume):
        reviewer.return_value = SimpleNamespace(uid=UID)
        for change in (
            {"acknowledged": False}, {"acknowledged": 1},
            {"now": 221}, {"page": {**PAGE, "pdf_page": 8}},
            {"page": {**PAGE, "image_sha256": "c" * 64}},
            {"delivery_challenge": "invalid"},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.call(**change)
        register.assert_not_called()

    @patch("source_review_receipt_service_v2.register_delivered_page_receipt")
    @patch("source_review_receipt_service_v2.resolve_admin_reviewer")
    def test_revoked_or_other_owner_never_registers(self, reviewer, register, consume):
        reviewer.side_effect = ValueError("revoked")
        with self.assertRaises(ValueError):
            self.call()
        reviewer.side_effect = None
        reviewer.return_value = SimpleNamespace(uid="00000000-0000-4000-8000-000000000000")
        with self.assertRaises(ValueError):
            self.call()
        register.assert_not_called()


if __name__ == "__main__":
    unittest.main()
