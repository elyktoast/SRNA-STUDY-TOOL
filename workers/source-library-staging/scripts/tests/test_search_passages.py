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
        rows = module.search(conn, "intubation", "895ed357-27c3-4d4b-a98a-77b0de20760c", section_id="295ed357-27c3-4d4b-a98a-77b0de20760c")
        self.assertIn("p.section_id=%s::uuid", conn.cur.sql)
        self.assertEqual(conn.cur.params, ["intubation", "895ed357-27c3-4d4b-a98a-77b0de20760c", "intubation", "295ed357-27c3-4d4b-a98a-77b0de20760c", 10])
        self.assertEqual(rows[0]["section_heading"], "Airway")
        self.assertFalse(rows[0]["citation_verified"])

    def test_book_and_section_filters(self):
        conn = FakeConnection()
        module.search(conn, "airway", "895ed357-27c3-4d4b-a98a-77b0de20760c", textbook_id="395ed357-27c3-4d4b-a98a-77b0de20760c", section_id="495ed357-27c3-4d4b-a98a-77b0de20760c")
        self.assertEqual(conn.cur.params[-3:], ["395ed357-27c3-4d4b-a98a-77b0de20760c", "495ed357-27c3-4d4b-a98a-77b0de20760c", 10])

    def test_recursive_chapter_search_scoped_to_owner(self):
        conn = FakeConnection()
        module.search(conn, "airway", "895ed357-27c3-4d4b-a98a-77b0de20760c", section_id="595ed357-27c3-4d4b-a98a-77b0de20760c",
                      include_subsections=True)
        self.assertIn("with recursive descendants", conn.cur.sql)
        self.assertIn("child.parent_section_id=parent.id", conn.cur.sql)
        self.assertIn("t0.owner_uid=%s", conn.cur.sql)
        self.assertEqual(conn.cur.params, ["airway", "895ed357-27c3-4d4b-a98a-77b0de20760c", "airway", "595ed357-27c3-4d4b-a98a-77b0de20760c", "895ed357-27c3-4d4b-a98a-77b0de20760c", 10])

    def test_recursive_search_requires_section(self):
        with self.assertRaisesRegex(ValueError, "Section ID required"):
            module.search(FakeConnection(), "airway", "895ed357-27c3-4d4b-a98a-77b0de20760c",
                          include_subsections=True)

    def test_invalid_owner_rejected(self):
        with self.assertRaisesRegex(ValueError, "owner UUID"):
            module.search(FakeConnection(), "airway", "not-a-uuid")

    def test_invalid_section_filter_rejected(self):
        with self.assertRaisesRegex(ValueError, "section UUID"):
            module.search(FakeConnection(), "airway", "895ed357-27c3-4d4b-a98a-77b0de20760c",
                          section_id="bad-section")

    def test_boolean_limit_rejected(self):
        with self.assertRaisesRegex(ValueError, "Limit"):
            module.search(FakeConnection(), "airway", "895ed357-27c3-4d4b-a98a-77b0de20760c",
                          limit=True)

    def test_missing_query_rejected(self):
        with self.assertRaisesRegex(ValueError, "query required"):
            module.search(FakeConnection(), " ", "895ed357-27c3-4d4b-a98a-77b0de20760c")


if __name__ == "__main__":
    unittest.main()
