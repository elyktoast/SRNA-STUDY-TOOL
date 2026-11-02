import unittest
from source_review_receipts_v2 import issue_receipt, verify_receipt

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"
OTHER = "d7c8ad4c-673d-4d87-a122-7d9bff4451bc"
KEY = b"review-only-server-secret-key-32-bytes-minimum"
ARGS = dict(reviewer_uid=UID, owner_uid=UID, source_sha256="a"*64,
            r2_key=UID+"/book.pdf", pdf_page=2, image_sha256="b"*64)

class ReceiptTests(unittest.TestCase):
    def test_valid_bound_receipt(self):
        receipt = issue_receipt(KEY, now=1000, **ARGS)
        nonce = verify_receipt(KEY, receipt, now=1100, **ARGS)
        self.assertEqual(len(nonce), 32)
        self.assertNotEqual(receipt, issue_receipt(KEY, now=1000, **ARGS))
    def test_expiry_and_future(self):
        receipt = issue_receipt(KEY, now=1000, **ARGS)
        for now in (999, 1301, 2000):
            with self.subTest(now=now), self.assertRaises(ValueError):
                verify_receipt(KEY, receipt, now=now, **ARGS)
    def test_tampering_and_wrong_key(self):
        receipt = issue_receipt(KEY, now=1000, **ARGS)
        for key, token in ((KEY, receipt+"x"), (b"x"*32, receipt), (KEY, "invalid")):
            with self.assertRaises(ValueError):
                verify_receipt(key, token, now=1001, **ARGS)
    def test_wrong_source_page_or_reviewer(self):
        receipt = issue_receipt(KEY, now=1000, **ARGS)
        for change in (dict(reviewer_uid=OTHER), dict(owner_uid=OTHER),
                       dict(source_sha256="c"*64), dict(pdf_page=3),
                       dict(image_sha256="d"*64), dict(r2_key=UID+"/other.pdf")):
            args = dict(ARGS, **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                verify_receipt(KEY, receipt, now=1001, **args)
    def test_weak_key_rejected(self):
        with self.assertRaises(ValueError):
            issue_receipt(b"short", now=1000, **ARGS)

if __name__ == "__main__":
    unittest.main()
