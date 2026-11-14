import unittest
from unittest.mock import patch

from source_review_receipt_service_v2 import register_delivered_page_receipt

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
PAGE = {"owner_uid": UID, "source_sha256": "a" * 64,
        "r2_key": UID + "/synthetic.pdf", "pdf_page": 1,
        "image_sha256": "b" * 64}
SECRET = b"staging-only-test-signing-secret-32bytes"


class Auth:
    def get_user(self, token):
        if token != "valid":
            raise ValueError("Invalid token")
        return {"id": UID, "active": True}


class Roles:
    def __init__(self, allowed=True):
        self.allowed = allowed
    def is_active_admin(self, uid):
        return self.allowed and uid == UID


class Transaction:
    def __init__(self):
        self.entered = False
    def __enter__(self):
        self.entered = True
    def __exit__(self, *args):
        return False


class Conn:
    def __init__(self):
        self.tx = Transaction()
    def transaction(self):
        return self.tx


def register(conn, **changes):
    params = dict(page=PAGE, access_token="valid", auth_provider=Auth(),
                  protected_role_store=Roles(), signing_secret=SECRET,
                  delivered_image_sha256=PAGE["image_sha256"], now=1000)
    params.update(changes)
    return register_delivered_page_receipt(conn, **params)


class ReceiptServiceTests(unittest.TestCase):
    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    def test_registers_nonce_before_returning_receipt(self, insert):
        conn = Conn()
        receipt = register(conn)
        self.assertEqual(len(receipt.split(".")), 2)
        self.assertTrue(conn.tx.entered)
        insert.assert_called_once()
        self.assertEqual(insert.call_args.kwargs["pdf_page"], 1)

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    def test_invalid_session_never_registers(self, insert):
        with self.assertRaises(ValueError):
            register(Conn(), access_token="forged")
        insert.assert_not_called()

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    def test_revoked_admin_never_registers(self, insert):
        with self.assertRaises(ValueError):
            register(Conn(), protected_role_store=Roles(False))
        insert.assert_not_called()

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    def test_mismatched_delivered_image_never_registers(self, insert):
        with self.assertRaisesRegex(ValueError, "Delivered image"):
            register(Conn(), delivered_image_sha256="c" * 64)
        insert.assert_not_called()

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    def test_cross_owner_page_never_registers(self, insert):
        with self.assertRaisesRegex(ValueError, "does not own"):
            register(Conn(), page={**PAGE, "owner_uid": "c" * 36})
        insert.assert_not_called()

    @patch("source_review_receipt_service_v2.time.time", return_value=1234.75)
    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    def test_single_timestamp_for_receipt_and_database_expiry(self, insert, clock):
        from source_review_receipts_v2 import verify_receipt
        receipt = register_delivered_page_receipt(
            Conn(), page=PAGE, access_token="valid",
            auth_provider=Auth(), protected_role_store=Roles(),
            signing_secret=SECRET,
            delivered_image_sha256=PAGE["image_sha256"])
        self.assertEqual(insert.call_args.kwargs["issued_at"], 1234.75)
        verify_receipt(
            SECRET, receipt, reviewer_uid=UID, owner_uid=UID,
            source_sha256=PAGE["source_sha256"], r2_key=PAGE["r2_key"],
            pdf_page=1, image_sha256=PAGE["image_sha256"], now=1234)

    @patch("source_review_receipt_service_v2.register_inspection_nonce", side_effect=ValueError("DB unavailable"))
    def test_database_failure_never_returns_receipt(self, insert):
        with self.assertRaisesRegex(ValueError, "DB unavailable"):
            register(Conn())



class AcknowledgmentExchangeTests(unittest.TestCase):
    def _exchange(self, conn, challenge, **changes):
        from source_review_receipt_service_v2 import register_acknowledged_page_receipt
        params = dict(page=PAGE, access_token="valid", auth_provider=Auth(),
                      protected_role_store=Roles(), signing_secret=SECRET,
                      delivery_challenge=challenge, acknowledged=True, now=1000)
        params.update(changes)
        return register_acknowledged_page_receipt(conn, **params)

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    @patch("source_review_receipt_service_v2.consume_inspection_nonce")
    def test_exchange_consumes_challenge_before_registering_receipt(self, consume, register_nonce):
        from source_review_delivery_challenge_v2 import issue_delivery_challenge
        challenge = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=1000)
        conn = Conn()
        receipt = self._exchange(conn, challenge)
        self.assertTrue(conn.tx.entered)
        self.assertEqual(len(receipt.split(".")), 2)
        consume.assert_called_once()
        register_nonce.assert_called_once()
        self.assertEqual(consume.call_args.kwargs["pdf_page"], PAGE["pdf_page"])

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    @patch("source_review_receipt_service_v2.consume_inspection_nonce")
    def test_replay_is_rejected_before_new_receipt(self, consume, register_nonce):
        from source_review_delivery_challenge_v2 import issue_delivery_challenge
        challenge = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=1000)
        consumed = set()
        def once(conn, *, nonce, **kwargs):
            if nonce in consumed:
                raise ValueError("Already consumed")
            consumed.add(nonce)
        consume.side_effect = once
        self._exchange(Conn(), challenge)
        with self.assertRaisesRegex(ValueError, "Already consumed"):
            self._exchange(Conn(), challenge)
        self.assertEqual(register_nonce.call_count, 1)

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    @patch("source_review_receipt_service_v2.consume_inspection_nonce")
    def test_revoked_role_or_missing_acknowledgment_cannot_consume(self, consume, register_nonce):
        from source_review_delivery_challenge_v2 import issue_delivery_challenge
        challenge = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=1000)
        for changes in ({"protected_role_store": Roles(False)},
                        {"acknowledged": False}, {"access_token": "invalid"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self._exchange(Conn(), challenge, **changes)
        consume.assert_not_called()
        register_nonce.assert_not_called()

    @patch("source_review_receipt_service_v2.register_inspection_nonce")
    @patch("source_review_receipt_service_v2.consume_inspection_nonce")
    def test_changed_image_or_expired_challenge_cannot_consume(self, consume, register_nonce):
        from source_review_delivery_challenge_v2 import issue_delivery_challenge
        challenge = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=1000)
        with self.assertRaises(ValueError):
            self._exchange(Conn(), challenge, page={**PAGE, "image_sha256": "c" * 64})
        with self.assertRaises(ValueError):
            self._exchange(Conn(), challenge, now=1121)
        consume.assert_not_called()
        register_nonce.assert_not_called()

if __name__ == "__main__":
    unittest.main()
