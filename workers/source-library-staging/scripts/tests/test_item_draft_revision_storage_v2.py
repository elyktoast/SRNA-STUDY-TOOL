"""No-network tests for revision persistence safety gates."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from item_draft_revision_storage_v2 import digest,save_revision,list_revisions
from unittest.mock import patch

OWNER="c003287a-10ce-4cc9-926e-ef7c3a162a26"
DRAFT="abc90a93-41f8-4d7c-8e27-94a609135572"

class Tests(unittest.TestCase):
    def test_digest_independent_of_object_key_order(self):
        self.assertEqual(digest({"a":1,"b":2}),digest({"b":2,"a":1}))
        self.assertNotEqual(digest({"a":1}),digest({"a":2}))
    def test_rejects_bad_parent_digest_before_database_access(self):
        with self.assertRaisesRegex(ValueError,"Expected parent digest"):
            save_revision(None,owner_uid=OWNER,draft_id=DRAFT,
                expected_parent_sha256="bad",reviewer_notes="Checked")
    def test_rejects_blank_review_notes_before_database_access(self):
        with self.assertRaisesRegex(ValueError,"Reviewer notes required"):
            save_revision(None,owner_uid=OWNER,draft_id=DRAFT,
                expected_parent_sha256="a"*64,reviewer_notes=" ")
    @patch("item_draft_revision_storage_v2.get_draft",return_value={"question":{"stem":"Original"}})
    def test_empty_history_exposes_original_as_head(self,fetch):
        class Cursor:
            def execute(self,sql,params):
                self.sql=sql
                self.params=params
            def fetchall(self): return []
            def __enter__(self): return self
            def __exit__(self,*args): pass
        class Conn:
            def cursor(self): return Cursor()
        result=list_revisions(Conn(),owner_uid=OWNER,draft_id=DRAFT)
        self.assertEqual(result["revisions"],[])
        self.assertEqual(result["current_question"],{"stem":"Original"})
        self.assertEqual(result["current_question_sha256"],digest({"stem":"Original"}))
        self.assertEqual(result["original_question_sha256"],digest({"stem":"Original"}))
        self.assertFalse(result["published"])

    @patch("item_draft_revision_storage_v2.get_draft",return_value={"question":{"stem":"Original"}})
    def test_history_returns_latest_revision_without_replacing_original(self,fetch):
        from datetime import datetime,timezone
        revised={"stem":"Revised"}
        row=(2,"revision-2",digest({"stem":"Previous"}),digest(revised),
             "Verified against source",datetime(2026,11,7,tzinfo=timezone.utc),revised)
        class Cursor:
            def execute(self,sql,params):pass
            def fetchall(self):return [row]
            def __enter__(self):return self
            def __exit__(self,*args):return False
        class Conn:
            def cursor(self):return Cursor()
        result=list_revisions(Conn(),owner_uid=OWNER,draft_id=DRAFT)
        self.assertEqual(result["current_question"],revised)
        self.assertEqual(result["current_question_sha256"],digest(revised))
        self.assertEqual(result["original_question_sha256"],digest({"stem":"Original"}))
        self.assertEqual(result["revisions"][0]["revision_number"],2)
        self.assertFalse(result["published"])

    @patch("item_draft_revision_storage_v2.get_draft")
    def test_stale_parent_prevents_write(self,fetch):
        fetch.return_value={"question":{"stem":"Original"},"evidence":[],
                            "textbook_id":"2a589498-aaa4-410f-b51a-00d3ab99eafd",
                            "published":False,"status":"pending_review"}
        class Cursor:
            def __init__(self,conn): self.conn=conn
            def execute(self,sql,params):
                self.conn.statements.append(sql)
            def fetchone(self):
                self.conn.reads+=1
                return (DRAFT,) if self.conn.reads==1 else None
            def __enter__(self): return self
            def __exit__(self,*args): return False
        class Conn:
            def __init__(self):self.reads=0;self.statements=[]
            def cursor(self):return Cursor(self)
        conn=Conn()
        with self.assertRaisesRegex(ValueError,"Stale revision"):
            save_revision(conn,owner_uid=OWNER,draft_id=DRAFT,
                expected_parent_sha256="a"*64,reviewer_notes="Checked source")
        self.assertFalse(any("insert into" in sql.lower() for sql in conn.statements))

    def test_rejects_untrusted_identity(self):
        with self.assertRaises(ValueError):
            save_revision(None,owner_uid="not-an-id",draft_id=DRAFT,
                expected_parent_sha256="a"*64,reviewer_notes="Checked")

if __name__=="__main__":unittest.main()
