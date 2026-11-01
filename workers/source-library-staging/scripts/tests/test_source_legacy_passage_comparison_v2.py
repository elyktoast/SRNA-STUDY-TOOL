import unittest
from source_legacy_passage_comparison_v2 import compare_indexed_passages, assess_provenance_backfill_eligibility

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "810040fc-da03-4fa5-bcc0-78c25957c325"


class Cursor:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def execute(self, sql, args):
        self.calls.append((sql, args))
    def fetchone(self): return (2,)
    def fetchall(self): return self.rows


class DB:
    def __init__(self, rows): self.cur = Cursor(rows)
    def cursor(self): return self.cur


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.fresh = [{"chunk_index": 0, "page_start": 1, "page_end": 1, "content": "Airway care"},
                      {"chunk_index": 1, "page_start": 2, "page_end": 2, "content": "Anesthesia safety"}]
        self.kwargs = {"textbook_id": BOOK, "owner_uid": OWNER,
                       "fresh_passages": self.fresh, "expected_page_count": 2,
                       "expected_source_sha256": "a" * 64}

    def test_exact_match_requires_ordered_equal_content_and_pages(self):
        db = DB([(0, 1, 1, "Airway care"), (1, 2, 2, "Anesthesia safety")])
        result = compare_indexed_passages(db, **self.kwargs)
        self.assertTrue(result["same_ordered_passages_and_pages"])
        self.assertFalse(result["provenance_backfilled"])
        self.assertFalse(result["approved_for_citation"])
        self.assertEqual(len(db.cur.calls), 2)
        self.assertTrue(all(sql.strip().startswith("SELECT") for sql, _ in db.cur.calls))

    def test_content_mismatch_is_reported(self):
        db = DB([(0, 1, 1, "Changed content"), (1, 2, 2, "Anesthesia safety")])
        result = compare_indexed_passages(db, **self.kwargs)
        self.assertFalse(result["same_ordered_passages_and_pages"])
        self.assertEqual(result["indexed_only_fingerprints"], 1)
        self.assertEqual(result["fresh_only_fingerprints"], 1)

    def test_reordering_is_not_accepted(self):
        db = DB([(0, 2, 2, "Anesthesia safety"), (1, 1, 1, "Airway care")])
        self.assertFalse(compare_indexed_passages(db, **self.kwargs)["same_ordered_passages_and_pages"])

    def test_verified_ocr_comparison_is_only_eligible_for_review(self):
        result = {"same_ordered_passages_and_pages": True,
                  "indexed_passage_count": 595, "fresh_passage_count": 595,
                  "indexed_only_fingerprints": 0, "fresh_only_fingerprints": 0}
        status = assess_provenance_backfill_eligibility(
            result, attestation_verified=True, extraction_ocr_enabled=True)
        self.assertTrue(status["eligible_for_operator_review"])
        self.assertFalse(status["operator_review_confirmed"])
        self.assertFalse(status["database_backfill_performed"])
        self.assertFalse(status["chapter_or_print_citations_approved"])
        status = assess_provenance_backfill_eligibility(
            result, attestation_verified=True, extraction_ocr_enabled=False,
            reviewer_confirmed=True)
        self.assertFalse(status["eligible_for_operator_review"])
        self.assertFalse(status["operator_review_confirmed"])

    def test_mismatched_comparison_can_never_unlock_provenance(self):
        result = {"same_ordered_passages_and_pages": False,
                  "indexed_passage_count": 595, "fresh_passage_count": 593,
                  "indexed_only_fingerprints": 4, "fresh_only_fingerprints": 2}
        status = assess_provenance_backfill_eligibility(
            result, attestation_verified=True, extraction_ocr_enabled=True,
            reviewer_confirmed=True)
        self.assertFalse(status["eligible_for_operator_review"])
        self.assertFalse(status["database_backfill_performed"])

    def test_missing_source_digest_blocks_query(self):
        db = DB([])
        with self.assertRaises(ValueError):
            compare_indexed_passages(db, **{**self.kwargs, "expected_source_sha256": "unknown"})
        self.assertEqual(db.cur.calls, [])


if __name__ == "__main__":
    unittest.main()
