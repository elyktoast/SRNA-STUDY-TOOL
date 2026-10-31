import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from apply_chapter_plan import apply_plan, validate_plan

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "810040fc-da03-4fa5-bcc0-78c25957c325"
FINGERPRINT = "a" * 64

def plan():
    return {"status": "prepared_not_applied", "review_fingerprint": FINGERPRINT,
            "citation_verified": False, "database_written": False,
            "sections": [{"kind": "Chapter", "heading": "Airway", "start_page": 21, "group": 1, "detector": "layout"},
                         {"kind": "Subsection", "heading": "Equipment", "start_page": 65, "group": 2, "detector": "text"}]}

class FakeCursor:
    def __init__(self, ready=True):
        self.calls = []
        self.ready = ready
        self.counter = 0
    def execute(self, sql, params):
        self.calls.append((sql, params))
    def fetchone(self):
        if len(self.calls) == 1:
            return (BOOK, 420) if self.ready else None
        self.counter += 1
        return (f"section-{self.counter}",)
    def __enter__(self): return self
    def __exit__(self, *args): pass

class FakeConnection:
    def __init__(self, ready=True): self.cur = FakeCursor(ready)
    def cursor(self): return self.cur
    def transaction(self): return self
    def __enter__(self): return self
    def __exit__(self, *args): pass

class ApplyTests(unittest.TestCase):
    def test_transactional_sequence(self):
        conn = FakeConnection()
        result = apply_plan(conn, OWNER, BOOK, plan(), FINGERPRINT)
        self.assertEqual(result["sections_applied"], 2)
        statements = [sql.lower() for sql, _ in conn.cur.calls]
        self.assertIn("for update", statements[0])
        self.assertIn("set section_id=null", statements[1])
        self.assertIn("delete from", statements[2])
        self.assertIn("update source_library_staging.passages p", statements[-1])
        self.assertFalse(result["citation_verified"])

    def test_wrong_fingerprint_does_not_query(self):
        conn = FakeConnection()
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            apply_plan(conn, OWNER, BOOK, plan(), "b" * 64)
        self.assertEqual(conn.cur.calls, [])

    def test_wrong_owner_no_mutation(self):
        conn = FakeConnection(ready=False)
        with self.assertRaisesRegex(ValueError, "not found"):
            apply_plan(conn, OWNER, BOOK, plan(), FINGERPRINT)
        self.assertEqual(len(conn.cur.calls), 1)

    def test_bad_order_rejected(self):
        p = plan()
        p["sections"][1]["start_page"] = 20
        with self.assertRaisesRegex(ValueError, "strictly increasing"):
            validate_plan(p, 420)

    def test_repeated_review_group_rejected(self):
        p = plan()
        p['sections'][1]['group'] = 1
        with self.assertRaisesRegex(ValueError, 'groups must be strictly increasing'):
            validate_plan(p, 420)

    def test_missing_chapter_rejected(self):
        p = plan()
        p["sections"] = p["sections"][1:]
        with self.assertRaisesRegex(ValueError, "without parent"):
            validate_plan(p, 420)

if __name__ == "__main__":
    unittest.main()
