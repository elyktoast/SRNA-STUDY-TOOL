"""No-network regression tests for private draft revalidation."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_draft_revalidation_v2 import revalidate

OWNER="c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK="2a589498-aaa4-410f-b51a-00d3ab99eafd"
DRAFT="abc90a93-41f8-4d7c-8e27-94a609135572"
PASSAGE="0e5e0c56-9c30-4c6d-8aef-4329446b198c"

class Cursor:
    def __init__(self, rows):
        self.rows=rows
        self.sql=None
        self.params=None
    def execute(self, sql, params):
        self.sql,self.params=sql,params
    def fetchall(self):
        return self.rows
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass

class Conn:
    def __init__(self, rows):
        self.cur=Cursor(rows)
    def cursor(self):
        return self.cur

def draft(question=None, status="pending_review"):
    return {"draft_id":DRAFT,"textbook_id":BOOK,"status":status,
            "published":False,
            "evidence":[{"passage_id":PASSAGE,"textbook_id":BOOK}],
            "question":question if question is not None else {
                "format":"MC","evidence":[{"passage_id":PASSAGE,
                "textbook_id":BOOK,"pdf_page":197}]}}

class RevalidationTests(unittest.TestCase):
    @patch("item_draft_revalidation_v2.get_draft")
    def test_reports_missing_excerpt_and_option_map_without_writing(self, get_draft):
        get_draft.return_value=draft()
        conn=Conn([(PASSAGE,BOOK,197,"Patient wide awake, wire cutters available.")])
        result=revalidate(conn,owner_uid=OWNER,draft_id=DRAFT)
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["generation_performed"])
        self.assertFalse(result["database_writes"])
        self.assertEqual(result["indexed_passages_found"],1)
        self.assertTrue(any(x["message"]=="Excerpt mismatch at index 0" for x in result["issues"]))
        self.assertTrue(any("option evidence map" in x["message"] for x in result["issues"]))
        self.assertIn("t.owner_uid=%s::uuid",conn.cur.sql)
        self.assertEqual(conn.cur.params[1:],(BOOK,OWNER))

    @patch("item_draft_revalidation_v2.get_draft")
    def test_missing_index_passage_blocks(self,get_draft):
        get_draft.return_value=draft()
        result=revalidate(Conn([]),owner_uid=OWNER,draft_id=DRAFT)
        self.assertTrue(any("missing from current index" in x["message"] for x in result["issues"]))
        self.assertFalse(result["can_publish"])

    @patch("item_draft_revalidation_v2.get_draft")
    def test_rejects_finalized_draft(self,get_draft):
        get_draft.return_value=draft(status="approved_for_bank")
        with self.assertRaisesRegex(ValueError,"Only unpublished drafts"):
            revalidate(Conn([]),owner_uid=OWNER,draft_id=DRAFT)

    @patch("item_draft_revalidation_v2.get_draft")
    def test_rejects_invalid_saved_evidence(self,get_draft):
        value=draft()
        value["evidence"]=None
        get_draft.return_value=value
        with self.assertRaisesRegex(ValueError,"Invalid saved evidence"):
            revalidate(Conn([]),owner_uid=OWNER,draft_id=DRAFT)

if __name__=="__main__":
    unittest.main()
