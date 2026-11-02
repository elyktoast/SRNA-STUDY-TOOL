import unittest
from unittest.mock import patch
from source_review_approval_service_v2 import approve_inspected_page
from source_review_receipts_v2 import issue_receipt

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
MANIFEST = {"owner_uid": UID, "sha256": "a"*64, "r2_key": UID+"/book.pdf", "pdf_page_count": 10}
KEY = b"review-only-server-secret-key-32-bytes-minimum"

class Auth:
    def get_user(self, token):
        if token != "valid": raise ValueError("Invalid session")
        return {"id": UID, "active": True}
class Roles:
    def is_active_admin(self, uid): return uid == UID
class Transaction:
    def __init__(self): self.entered = False; self.exited = False; self.failed = False
    def __enter__(self): self.entered = True
    def __exit__(self, kind, value, tb): self.exited = True; self.failed = kind is not None; return False
class Conn:
    def __init__(self): self.tx = Transaction()
    def transaction(self): return self.tx

def approve(conn, receipt):
    return approve_inspected_page(conn, MANIFEST, pdf_page=2,
        review_note="Original image inspected", receipt=receipt,
        image_sha256="b"*64, receipt_secret=KEY, access_token="valid",
        auth_provider=Auth(), protected_role_store=Roles(), now=1001)

class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.receipt = issue_receipt(KEY, reviewer_uid=UID, owner_uid=UID,
            source_sha256=MANIFEST["sha256"], r2_key=MANIFEST["r2_key"],
            pdf_page=2, image_sha256="b"*64, now=1000)
    @patch("source_review_approval_service_v2.record_page_decision", return_value=1)
    @patch("source_review_approval_service_v2.consume_inspection_nonce", return_value=True)
    def test_single_transaction(self, consume, write):
        conn = Conn()
        self.assertEqual(approve(conn, self.receipt), 1)
        self.assertTrue(conn.tx.entered and conn.tx.exited)
        consume.assert_called_once()
        self.assertTrue(write.call_args.kwargs["_verified_inspection"])
    @patch("source_review_approval_service_v2.record_page_decision", side_effect=ValueError("DB failure"))
    @patch("source_review_approval_service_v2.consume_inspection_nonce", return_value=True)
    def test_write_failure_rolls_back(self, consume, write):
        conn = Conn()
        with self.assertRaises(ValueError):
            approve(conn, self.receipt)
        self.assertTrue(conn.tx.failed)
    @patch("source_review_approval_service_v2.record_page_decision")
    @patch("source_review_approval_service_v2.consume_inspection_nonce", side_effect=ValueError("replayed"))
    def test_replayed_nonce_never_writes(self, consume, write):
        conn = Conn()
        with self.assertRaises(ValueError):
            approve(conn, self.receipt)
        write.assert_not_called()
        self.assertTrue(conn.tx.failed)
    @patch("source_review_approval_service_v2.consume_inspection_nonce")
    def test_tampered_receipt_never_consumed(self, consume):
        with self.assertRaises(ValueError):
            approve(Conn(), self.receipt+"x")
        consume.assert_not_called()

if __name__ == "__main__":
    unittest.main()
