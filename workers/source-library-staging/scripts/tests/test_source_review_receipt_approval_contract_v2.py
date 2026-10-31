"""Staging receipt issuance -> approval integration contract.

No live HTTP endpoint or real PostgreSQL is exercised. The in-memory nonce
registry models the one-time database contract to catch binding/replay errors.
"""
import unittest
from unittest.mock import patch

from source_review_receipt_service_v2 import register_delivered_page_receipt
from source_review_approval_service_v2 import approve_inspected_page

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
PAGE = {"owner_uid": UID, "r2_key": UID + "/synthetic.pdf",
        "source_sha256": "a" * 64, "pdf_page": 1,
        "image_sha256": "b" * 64}
MANIFEST = {"owner_uid": UID, "r2_key": PAGE["r2_key"],
            "sha256": PAGE["source_sha256"], "pdf_page_count": 1}
SECRET = b"synthetic-only-signing-secret-32-bytes-long"


class Auth:
    def get_user(self, token):
        return {"id": UID, "active": token == "valid"}


class Roles:
    def is_active_admin(self, uid):
        return uid == UID


class Tx:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class Conn:
    def transaction(self):
        return Tx()


class ReceiptApprovalContractTests(unittest.TestCase):
    def setUp(self):
        self.nonces = set()
        self.conn = Conn()
        self.auth = Auth()
        self.roles = Roles()

    def issue(self):
        return register_delivered_page_receipt(
            self.conn, page=PAGE, access_token="valid",
            auth_provider=self.auth, protected_role_store=self.roles,
            signing_secret=SECRET, delivered_image_sha256=PAGE["image_sha256"],
            now=1000)

    def approve(self, receipt, *, image_sha=None, manifest=None):
        return approve_inspected_page(
            self.conn, manifest or MANIFEST, pdf_page=1,
            review_note="Synthetic inspected page", receipt=receipt,
            image_sha256=image_sha or PAGE["image_sha256"],
            receipt_secret=SECRET, access_token="valid",
            auth_provider=self.auth, protected_role_store=self.roles, now=1001)

    def test_issue_approve_and_replay_denied(self):
        def register(conn, **kwargs):
            self.assertNotIn(kwargs["nonce"], self.nonces)
            self.nonces.add(kwargs["nonce"])
        def consume(conn, **kwargs):
            if kwargs["nonce"] not in self.nonces:
                raise ValueError("Nonce already consumed")
            self.nonces.remove(kwargs["nonce"])
        with patch("source_review_receipt_service_v2.register_inspection_nonce", side_effect=register), \
             patch("source_review_approval_service_v2.consume_inspection_nonce", side_effect=consume), \
             patch("source_review_approval_service_v2.record_page_decision", return_value=1) as decision:
            receipt = self.issue()
            self.assertEqual(self.approve(receipt), 1)
            self.assertEqual(self.nonces, set())
            with self.assertRaisesRegex(ValueError, "already consumed"):
                self.approve(receipt)
            decision.assert_called_once()

    def test_tampered_image_never_consumes(self):
        with patch("source_review_receipt_service_v2.register_inspection_nonce") as register, \
             patch("source_review_approval_service_v2.consume_inspection_nonce") as consume:
            receipt = self.issue()
            register.assert_called_once()
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self.approve(receipt, image_sha="c" * 64)
            consume.assert_not_called()

    def test_replaced_manifest_never_consumes(self):
        with patch("source_review_receipt_service_v2.register_inspection_nonce"), \
             patch("source_review_approval_service_v2.consume_inspection_nonce") as consume:
            receipt = self.issue()
            with self.assertRaisesRegex(ValueError, "mismatch"):
                self.approve(receipt, manifest={**MANIFEST, "sha256": "c" * 64})
            consume.assert_not_called()


if __name__ == "__main__":
    unittest.main()
