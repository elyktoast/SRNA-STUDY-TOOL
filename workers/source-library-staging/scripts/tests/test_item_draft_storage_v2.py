import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from item_draft_storage_v2 import save, review, list_drafts, get_draft

OWNER="c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK="2a589498-aaa4-410f-b51a-00d3ab99eafd"
DRAFT="1c05897c-16e8-4d09-9dc5-cf44ad9a4f9d"

class Cursor:
    def __init__(self, row=None, rows=None):
        self.row,self.rows=row,rows or []
        self.sql,self.params=None,None
    def execute(self, sql, params):
        self.sql,self.params=sql,params
    def fetchone(self):
        return self.row
    def fetchall(self):
        return self.rows
    def __enter__(self):
        return self
    def __exit__(self,*args):
        pass
class Conn:
    def __init__(self,cur):
        self.cur=cur
    def cursor(self):
        return self.cur

def payload():
    return dict(owner_uid=OWNER,textbook_id=BOOK,topic="airway",
                mode="NCE",format="MC",domain="I",section="A",
                objective="I.A.1",provider="test",model="test",
                question={"stem":"Example"},screening={"issues":[]},
                evidence=[{"passage_id":"p1","textbook_id":BOOK}])

class StorageTests(unittest.TestCase):
    def test_save_scopes_textbook_to_owner(self):
        cur=Cursor(row=(DRAFT,))
        result=save(Conn(cur),payload())
        self.assertEqual(result["draft_id"],DRAFT)
        self.assertFalse(result["published"])
        self.assertIn("t.owner_uid=%s::uuid",cur.sql)
        self.assertEqual(cur.params[-2:],(BOOK,OWNER))

    def test_save_rejects_unowned_textbook(self):
        with self.assertRaises(ValueError):
            save(Conn(Cursor(row=None)),payload())

    def test_review_requires_owner_and_unreviewed_status(self):
        cur=Cursor(row=(DRAFT,))
        result=review(Conn(cur),owner_uid=OWNER,reviewer_uid=OWNER,
                      draft_id=DRAFT,status="approved_for_bank",
                      notes="Evidence reviewed")
        self.assertFalse(result["published"])
        self.assertIn("d.status in ('pending_review','needs_revision')",cur.sql)
        self.assertEqual(cur.params[-2:],(OWNER,OWNER))

    def test_get_draft_returns_full_private_record(self):
        now = datetime(2026,11,2,tzinfo=timezone.utc)
        row = (DRAFT,BOOK,"airway","NCE","MC","I","A","I.A.1",
               "test","test",{"stem":"Example"},{"issues":[]},
               [{"passage_id":"p1","textbook_id":BOOK}],
               "pending_review",None,None,None,now,now)
        cur = Cursor(row=row)
        result = get_draft(Conn(cur),owner_uid=OWNER,draft_id=DRAFT)
        self.assertEqual(result["question"]["stem"],"Example")
        self.assertEqual(result["evidence"][0]["textbook_id"],BOOK)
        self.assertFalse(result["published"])
        self.assertEqual(cur.params,(DRAFT,OWNER,OWNER))
        self.assertIn("t.owner_uid=%s::uuid",cur.sql)

    def test_get_draft_rejects_missing_or_unowned_record(self):
        with self.assertRaisesRegex(ValueError,"Draft not found"):
            get_draft(Conn(Cursor(row=None)),owner_uid=OWNER,draft_id=DRAFT)

    def test_list_is_owner_scoped_and_bounded(self):
        cur=Cursor(rows=[(DRAFT,"airway","NCE","MC","pending_review",
                         datetime(2026,11,2,tzinfo=timezone.utc),BOOK)])
        rows=list_drafts(Conn(cur),owner_uid=OWNER)
        self.assertEqual(rows[0]["draft_id"],DRAFT)
        self.assertEqual(cur.params,(OWNER,OWNER,50))
        with self.assertRaises(ValueError):
            list_drafts(Conn(cur),owner_uid=OWNER,limit=101)

if __name__=="__main__":
    unittest.main()
