import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_review_db_v2 import load_approved_pages
from source_review_authorization_v2 import approved_pages_for_import

MANIFEST = {"owner_uid":"owner", "sha256":"a"*64,
            "r2_key":"owner/book.pdf", "pdf_page_count":10}
class Cursor:
    def __init__(self, rows):
        self.rows=rows
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def execute(self,sql,params):
        assert "%s" in sql and len(params)==4
        assert "revoked_at is null" in sql
        assert params[3]=="reviewer"
    def fetchall(self): return self.rows
class Connection:
    def __init__(self,rows): self.rows=rows
    def cursor(self): return Cursor(self.rows)

class DatabaseApprovalTests(unittest.TestCase):
    def test_loaded_approval_matches_source(self):
        approval=load_approved_pages(Connection([(2,)]),MANIFEST,
            authenticated_reviewer_uid="reviewer",reviewer_is_admin=True)
        self.assertEqual(approved_pages_for_import(MANIFEST,approval,
            authenticated_reviewer_uid="reviewer",reviewer_is_admin=True),frozenset({2}))
    def test_no_admin_rejected_before_query(self):
        with self.assertRaisesRegex(ValueError,"Verified admin"):
            load_approved_pages(None,MANIFEST,
                authenticated_reviewer_uid="reviewer",reviewer_is_admin=False)
    def test_duplicate_db_rows_rejected(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            load_approved_pages(Connection([(2,),(2,)]),MANIFEST,
                authenticated_reviewer_uid="reviewer",reviewer_is_admin=True)

if __name__=="__main__":
    unittest.main()
