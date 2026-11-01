"""No database needed: verify SQL safety and chapter/page search boundaries."""
import unittest
from source_retrieval_staging_v2 import search_passages, audit_textbook_retrieval

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "810040fc-da03-4fa5-bcc0-78c25957c325"
CHAPTER = "895ed357-27c3-4d4b-a98a-77b0de20760c"


class Cursor:
    def __init__(self):
        self.sql = None
        self.params = None
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def execute(self, sql, params):
        self.sql, self.params = sql, params
    def fetchall(self):
        return [(4, 30, 30, "Airway management", CHAPTER, 1.25)]


class Connection:
    def __init__(self):
        self.cur = Cursor()
    def cursor(self):
        return self.cur


class RetrievalTests(unittest.TestCase):
    def test_owner_book_chapter_and_page_constraints_are_parameterized(self):
        conn = Connection()
        rows = search_passages(conn, owner_uid=OWNER, textbook_id=BOOK,
                               query="airway management", chapter_id=CHAPTER,
                               page_start=20, page_end=35, limit=8)
        sql, values = conn.cur.sql, conn.cur.params
        self.assertEqual(values, ("airway management", OWNER, BOOK,
                                  "airway management", CHAPTER, 20, 35, 8))
        for fragment in ("t.owner_uid = %s::uuid", "t.id = %s::uuid",
                         "t.status = 'ready'", "p.section_id = %s::uuid",
                         "p.page_end >= %s", "p.page_start <= %s",
                         "ORDER BY rank DESC"):
            self.assertIn(fragment, sql)
        self.assertIn("source_library_staging.source_versions v", sql)
        self.assertIn("v.owner_uid = t.owner_uid", sql)
        self.assertNotIn(OWNER, sql)
        self.assertNotIn("airway management", sql)
        self.assertEqual(rows[0]["page_start"], 30)
        self.assertEqual(rows[0]["section_id"], CHAPTER)

    def test_unfiltered_retrieval_remains_owner_and_textbook_scoped(self):
        conn = Connection()
        search_passages(conn, owner_uid=OWNER, textbook_id=BOOK, query="oxygen")
        self.assertNotIn("p.section_id = %s::uuid", conn.cur.sql)
        self.assertNotIn("p.page_end >=", conn.cur.sql)
        self.assertEqual(conn.cur.params[-1], 20)
        self.assertIn("t.owner_uid = %s::uuid", conn.cur.sql)

    def test_audit_reports_missing_chapters_without_overclaiming_citations(self):
        conn = Connection()
        conn.cur.fetchall = lambda: []
        conn.cur.fetchone = lambda: ("ready", 420, 595, 0, 0, 0)
        status = audit_textbook_retrieval(conn, owner_uid=OWNER, textbook_id=BOOK)
        self.assertTrue(status["text_search_ready"])
        self.assertTrue(status["physical_page_reference_ready"])
        self.assertFalse(status["chapter_filter_ready"])
        self.assertFalse(status["print_page_citations_verified"])
        self.assertFalse(status["source_provenance_ready"])
        self.assertFalse(status["chapter_publication_ready"])
        self.assertEqual(conn.cur.params, (BOOK, OWNER))
        self.assertIn("t.owner_uid=%s::uuid", conn.cur.sql)

    def test_audit_requires_indexed_chapter_links(self):
        conn = Connection()
        conn.cur.fetchone = lambda: ("ready", 420, 595, 4, 0, 1)
        status = audit_textbook_retrieval(conn, owner_uid=OWNER, textbook_id=BOOK)
        self.assertFalse(status["chapter_filter_ready"])
        conn.cur.fetchone = lambda: ("ready", 420, 595, 4, 440, 1)
        status = audit_textbook_retrieval(conn, owner_uid=OWNER, textbook_id=BOOK)
        self.assertTrue(status["chapter_filter_ready"])
        conn.cur.fetchone = lambda: ("ready", 420, 595, 4, 440, 0)
        self.assertFalse(audit_textbook_retrieval(conn, owner_uid=OWNER, textbook_id=BOOK)["chapter_filter_ready"])
        conn.cur.fetchone = lambda: ("ready", 420, 595, 0, 0, 1)
        self.assertTrue(audit_textbook_retrieval(conn, owner_uid=OWNER, textbook_id=BOOK)["chapter_publication_ready"])

    def test_invalid_requests_fail_before_database_access(self):
        cases = [
            {"owner_uid": "other"},
            {"textbook_id": "broken"},
            {"query": ""},
            {"query": " "},
            {"query": "?" },
            {"query": "x" * 201},
            {"chapter_id": "not-uuid"},
            {"page_start": 0},
            {"page_end": 100001},
            {"page_start": 50, "page_end": 49},
            {"limit": 0},
            {"limit": True},
            {"limit": 51},
        ]
        for override in cases:
            conn = Connection()
            args = {"owner_uid": OWNER, "textbook_id": BOOK, "query": "airway"}
            args.update(override)
            with self.subTest(override=override), self.assertRaises(ValueError):
                search_passages(conn, **args)
            self.assertIsNone(conn.cur.sql)


if __name__ == "__main__":
    unittest.main()
