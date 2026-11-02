import unittest
from contextlib import nullcontext
from source_chapter_boundaries_v2 import validate_chapter_boundaries, assign_passages_to_chapters, persist_verified_chapters


class ChapterBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.chapters = [
            {"heading": "Airway", "start_page": 5, "verified_against_pdf": True},
            {"heading": "Regional", "start_page": 18, "verified_against_pdf": True},
        ]

    def test_validated_boundaries_and_front_matter(self):
        self.assertEqual(len(validate_chapter_boundaries(self.chapters, pdf_page_count=30)), 2)
        passages = [{"page_start": 1, "page_end": 1},
                    {"page_start": 6, "page_end": 6},
                    {"page_start": 17, "page_end": 18},
                    {"page_start": 20, "page_end": 20}]
        self.assertEqual(assign_passages_to_chapters(passages, self.chapters, pdf_page_count=30),
                         [None, 0, None, 1])

    def test_invalid_boundaries_are_rejected(self):
        cases = [
            [], [{"heading": "Guess", "start_page": 3, "verified_against_pdf": False}],
            [{"heading": "Guess", "start_page": 3, "verified_against_pdf": 1}],
            [{"heading": "", "start_page": 1, "verified_against_pdf": True}],
            [{"heading": "Airway", "start_page": 0, "verified_against_pdf": True}],
            [{"heading": "Airway", "start_page": 31, "verified_against_pdf": True}],
            [self.chapters[1], self.chapters[0]],
            [self.chapters[0], self.chapters[0]],
            [{**self.chapters[0], "printed_page": 1}],
        ]
        for case in cases:
            with self.subTest(case=case), self.assertRaises(ValueError):
                validate_chapter_boundaries(case, pdf_page_count=30)

    def test_persistence_fails_closed_without_admin_and_digest(self):
        class NoDb:
            def transaction(self):
                raise AssertionError("Database should not be touched")
        kwargs = dict(owner_uid="c003287a-10ce-4cc9-926e-ef7c3a162a26",
                      textbook_id="810040fc-da03-4fa5-bcc0-78c25957c325",
                      boundaries=self.chapters,
                      authenticated_reviewer_uid="895ed357-27c3-4d4b-a98a-77b0de20760c")
        with self.assertRaises(PermissionError):
            persist_verified_chapters(NoDb(), **kwargs)
        with self.assertRaises(ValueError):
            persist_verified_chapters(NoDb(), reviewer_is_admin=True, **kwargs)

    def test_transaction_creates_chapters_and_links_only_unambiguous_passages(self):
        class Cursor:
            def __init__(self):
                self.queries = []
                self.results = iter([
                    (30, "ready"), ("a" * 64,), (0,),
                    [(0, 1, 1), (1, 6, 6), (2, 17, 18), (3, 20, 20)],
                    ("895ed357-27c3-4d4b-a98a-77b0de20760c",),
                    ("e765d954-1ab3-44e8-a82e-f7521f93f591",),
                ])
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def execute(self, sql, params):
                self.queries.append((sql, params))
            def fetchone(self): return next(self.results)
            def fetchall(self): return next(self.results)
        class Connection:
            def __init__(self): self.cur = Cursor()
            def transaction(self): return nullcontext()
            def cursor(self): return self.cur
        conn = Connection()
        result = persist_verified_chapters(
            conn, owner_uid="c003287a-10ce-4cc9-926e-ef7c3a162a26",
            textbook_id="810040fc-da03-4fa5-bcc0-78c25957c325",
            boundaries=self.chapters,
            authenticated_reviewer_uid="895ed357-27c3-4d4b-a98a-77b0de20760c",
            reviewer_is_admin=True, expected_source_sha256="a" * 64)
        self.assertEqual((result["chapters_created"], result["passages_linked"],
                          result["passages_unassigned"]), (2, 2, 2))
        self.assertEqual(len([q for q, _ in conn.cur.queries if "UPDATE source_library_staging.passages" in q]), 2)
        self.assertFalse(result["print_page_citations_verified"])

    def test_invalid_passage_pages_are_rejected(self):
        for passage in [{"page_start": 0, "page_end": 1},
                        {"page_start": 3, "page_end": 31},
                        {"page_start": 10, "page_end": 9},
                        {"page_start": True, "page_end": 10}]:
            with self.subTest(passage=passage), self.assertRaises(ValueError):
                assign_passages_to_chapters([passage], self.chapters, pdf_page_count=30)


if __name__ == "__main__":
    unittest.main()
