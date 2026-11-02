import unittest
from pathlib import Path

SQL = (Path(__file__).resolve().parents[1] / "sql" / "page_review_approvals_v2.sql").read_text()

class ApprovalSchemaContractTests(unittest.TestCase):
    def test_private_by_default(self):
        self.assertIn("enable row level security", SQL)
        self.assertIn("force row level security", SQL)
        self.assertIn("revoke all", SQL)
        self.assertIn("revoke create on schema source_library_staging from public, anon, authenticated", SQL)
        self.assertIn("from public, anon, authenticated", SQL)
        self.assertNotIn("create policy", SQL.lower())
    def test_source_and_reviewer_scoped(self):
        for field in ("owner_uid", "source_sha256", "r2_key", "pdf_page",
                      "reviewer_uid", "decision", "revoked_at"):
            self.assertIn(field, SQL)
        self.assertIn("unique (owner_uid, source_sha256, r2_key, pdf_page, reviewer_uid)", SQL)
    def test_revocation_and_approval_index(self):
        self.assertIn("where decision = 'approved' and revoked_at is null", SQL)

if __name__ == "__main__":
    unittest.main()
