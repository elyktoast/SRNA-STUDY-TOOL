import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_review_authorization_v2 import TrustedReviewApproval, approved_pages_for_import
from import_extraction import import_passages

SOURCE = {"owner_uid": "owner", "sha256": "a"*64, "r2_key": "owner/book.pdf",
          "pdf_page_count": 10, "low_text_pages": [2], "ocr_failed_pages": [],
          "requires_ocr_review": True}
APPROVAL = TrustedReviewApproval("owner", "a"*64, "owner/book.pdf", "reviewer", frozenset({2}))

class AuthorizationTests(unittest.TestCase):
    def test_verified_admin_approval(self):
        self.assertEqual(approved_pages_for_import(SOURCE, APPROVAL,
            authenticated_reviewer_uid="reviewer", reviewer_is_admin=True), frozenset({2}))
    def test_rejects_wrong_reviewer(self):
        with self.assertRaisesRegex(ValueError, "reviewer mismatch"):
            approved_pages_for_import(SOURCE, APPROVAL,
                authenticated_reviewer_uid="attacker", reviewer_is_admin=True)
    def test_rejects_untrusted_json(self):
        with self.assertRaisesRegex(ValueError, "Trusted server-side"):
            approved_pages_for_import(SOURCE, {"approved_pages": [2]},
                authenticated_reviewer_uid="reviewer", reviewer_is_admin=True)
    def test_rejects_non_admin(self):
        with self.assertRaisesRegex(ValueError, "admin"):
            approved_pages_for_import(SOURCE, APPROVAL,
                authenticated_reviewer_uid="reviewer", reviewer_is_admin=False)
    def test_central_import_rejects_missing_authentication(self):
        with self.assertRaisesRegex(ValueError, "Authenticated reviewer"):
            import_passages(None, SOURCE, None, reviewer_is_admin=True)

if __name__ == "__main__":
    unittest.main()
