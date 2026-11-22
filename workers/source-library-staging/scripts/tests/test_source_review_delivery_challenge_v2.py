import unittest

from source_review_delivery_challenge_v2 import (
    issue_delivery_challenge, verify_delivery_challenge)

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
PAGE = {"owner_uid": UID, "r2_key": UID + "/book.pdf",
        "source_sha256": "a" * 64, "image_sha256": "b" * 64,
        "pdf_page": 7}
SECRET = b"strong-staging-secret-not-for-production-123"


class DeliveryChallengeTests(unittest.TestCase):
    def test_exact_identity_and_expiry(self):
        token = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=100)
        self.assertEqual(len(verify_delivery_challenge(
            SECRET, token, reviewer_uid=UID, page=PAGE, now=220)), 32)
        with self.assertRaises(ValueError):
            verify_delivery_challenge(SECRET, token, reviewer_uid=UID, page=PAGE, now=221)
        with self.assertRaises(ValueError):
            verify_delivery_challenge(SECRET, token, reviewer_uid=UID, page=PAGE, now=99)

    def test_rejects_cross_page_source_image_and_reviewer(self):
        token = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=100)
        for change in ({"pdf_page": 8}, {"r2_key": UID + "/other.pdf"},
                       {"source_sha256": "c" * 64}, {"image_sha256": "c" * 64},
                       {"owner_uid": "00000000-0000-4000-8000-000000000000"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_delivery_challenge(
                    SECRET, token, reviewer_uid=UID,
                    page={**PAGE, **change}, now=100)

    def test_tampering_wrong_secret_and_weak_key(self):
        token = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=100)
        for secret, challenge in ((SECRET, token + "x"),
                                  (b"different-strong-secret-for-tests-123", token),
                                  (SECRET, "invalid")):
            with self.subTest(challenge=challenge[-12:]), self.assertRaises(ValueError):
                verify_delivery_challenge(
                    secret, challenge, reviewer_uid=UID, page=PAGE, now=100)
        with self.assertRaises(ValueError):
            issue_delivery_challenge(b"weak", reviewer_uid=UID, page=PAGE)

    def test_distinct_challenges_and_no_receipt_confusion(self):
        from source_review_receipts_v2 import verify_receipt
        first = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=100)
        second = issue_delivery_challenge(SECRET, reviewer_uid=UID, page=PAGE, now=100)
        self.assertNotEqual(first, second)
        with self.assertRaises(ValueError):
            verify_receipt(
                SECRET, first, reviewer_uid=UID, owner_uid=UID,
                source_sha256=PAGE["source_sha256"], r2_key=PAGE["r2_key"],
                pdf_page=7, image_sha256=PAGE["image_sha256"], now=100)


if __name__ == "__main__":
    unittest.main()
