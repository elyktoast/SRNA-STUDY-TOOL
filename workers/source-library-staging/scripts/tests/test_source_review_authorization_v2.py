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
    def test_flood_divider_handoff_requires_exact_trusted_page_coverage(self):
        # A chat-based manual inspection report is NOT a database approval.
        pages = frozenset((7, 10, 26, 29, 104, 2846, 2882))
        owner = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
        sha = "c831b51da96bd4d4178ea6913919d6b4a167c547590d4caf6c07c82e948c5aba"
        key = owner + "/1878c3ce-7202-4569-82a0-5029d77b2054.pdf"
        manifest = {"owner_uid": owner, "sha256": sha, "r2_key": key,
                    "pdf_page_count": 3011, "low_text_pages": sorted(pages),
                    "ocr_failed_pages": [], "ocr_review_pages": [],
                    "requires_ocr_review": True}
        with self.assertRaisesRegex(ValueError, "Trusted server-side"):
            approved_pages_for_import(
                manifest, {"reviewed_pages": sorted(pages), "note": "non-content divider"},
                authenticated_reviewer_uid=owner, reviewer_is_admin=True)
        incomplete = TrustedReviewApproval(owner, sha, key, owner, pages - {104})
        approved = approved_pages_for_import(
            manifest, incomplete, authenticated_reviewer_uid=owner,
            reviewer_is_admin=True)
        self.assertFalse(pages.issubset(approved))
        complete = TrustedReviewApproval(owner, sha, key, owner, pages)
        approved = approved_pages_for_import(
            manifest, complete, authenticated_reviewer_uid=owner,
            reviewer_is_admin=True)
        self.assertEqual(approved, pages)
        with self.assertRaisesRegex(ValueError, "source mismatch"):
            approved_pages_for_import(
                manifest, TrustedReviewApproval(owner, "0" * 64, key, owner, pages),
                authenticated_reviewer_uid=owner, reviewer_is_admin=True)

    def test_central_import_rejects_missing_authentication(self):
        with self.assertRaisesRegex(ValueError, "Trusted server-side review approval required"):
            import_passages(None, SOURCE, None, reviewer_is_admin=True)

if __name__ == "__main__":
    unittest.main()
