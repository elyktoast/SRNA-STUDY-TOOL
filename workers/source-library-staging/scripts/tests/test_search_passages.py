"""Unit tests for chapter-filtered search query construction without a database."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("search_passages", ROOT / "search_passages.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FakeCursor:
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
        return [("passage", "book", "book.pdf", 0, 3, 3,
                 "section", "Airway", 0.5, "Intubation confirmation")]


class FakeConnection:
    def __init__(self):
        self.cur = FakeCursor()

    def cursor(self):
        return self.cur


class SearchTests(unittest.TestCase):
    def test_section_filter_and_result_metadata(self):
        conn = FakeConnection()
        rows = module.search(conn, "intubation", "owner-uid", section_id="section-uid")
        self.assertIn("p.section_id=%s::uuid", conn.cur.sql)
        self.assertEqual(conn.cur.params, ["intubation", "owner-uid", "intubation", "section-uid", 10])
        self.assertEqual(rows[0]["section_heading"], "Airway")
        self.assertFalse(rows[0]["citation_verified"])

    def test_book_and_section_filters(self):
        conn = FakeConnection()
        module.search(conn, "airway", "owner", textbook_id="book-id", section_id="section-id")
        self.assertEqual(conn.cur.params[-3:], ["book-id", "section-id", 10])

    def test_recursive_chapter_search_scoped_to_owner(self):
        conn = FakeConnection()
        module.search(conn, "airway", "owner", section_id="chapter",
                      include_subsections=True)
        self.assertIn("with recursive descendants", conn.cur.sql)
        self.assertIn("child.parent_section_id=parent.id", conn.cur.sql)
        self.assertIn("t0.owner_uid=%s", conn.cur.sql)
        self.assertEqual(conn.cur.params, ["airway", "owner", "airway", "chapter", "owner", 10])

    def test_recursive_search_requires_section(self):
        with self.assertRaisesRegex(ValueError, "Section ID required"):
            module.search(FakeConnection(), "airway", "owner",
                          include_subsections=True)

    def test_missing_query_rejected(self):
        with self.assertRaisesRegex(ValueError, "query required"):
            module.search(FakeConnection(), " ", "owner")


if __name__ == "__main__":
    unittest.main()
