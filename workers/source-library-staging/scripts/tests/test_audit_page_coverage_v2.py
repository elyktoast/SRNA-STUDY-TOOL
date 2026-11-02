"""Read-only coverage report regression tests; no live staging credentials."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from audit_page_coverage_v2 import audit


class Cursor:
    def __init__(self, records):
        self.records = iter(records)
        self.calls = []
    def execute(self, sql, params=None):
        self.calls.append((sql, params))
    def fetchone(self):
        return next(self.records)
    def fetchall(self):
        return next(self.records)
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class Conn:
    def __init__(self, records):
        self.cur = Cursor(records)
    def cursor(self):
        return self.cur
    def transaction(self):
        return self
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class CoverageTests(unittest.TestCase):
    def test_missing_pages_and_ocr_block_unrestricted_generation(self):
        conn = Conn([("book.pdf", "ready", 5, 2, True), [(1, 1), (3, 4)], (0, 0)])
        result = audit(conn, "book-id")
        self.assertEqual(result["uncovered_pages"], [2, 5])
        self.assertEqual(result["covered_pages"], 3)
        self.assertEqual(result["coverage_percent"], 60)
        self.assertFalse(result["ready_for_unrestricted_generation"])
        self.assertTrue(any("read only" in sql.lower() for sql, _ in conn.cur.calls))

    def test_invalid_ranges_never_count_as_coverage(self):
        conn = Conn([("book.pdf", "ready", 3, 0, False),
                     [(1, 3), (0, 1), (2, 4), (3, 2)], (1, 1)])
        result = audit(conn, "book-id")
        self.assertEqual(result["invalid_passage_ranges"], 3)
        self.assertFalse(result["ready_for_unrestricted_generation"])

    def test_clean_book_is_eligible(self):
        conn = Conn([("book.pdf", "ready", 2, 0, False), [(1, 2)], (1, 0)])
        self.assertTrue(audit(conn, "book-id")["ready_for_unrestricted_generation"])


if __name__ == "__main__":
    unittest.main()
