import unittest
from unittest.mock import patch
from source_retrieval_acceptance_v2 import verify_retrieval_against_extraction

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "810040fc-da03-4fa5-bcc0-78c25957c325"
ROWS = [{"chunk_index": i, "page_start": i + 1, "page_end": i + 1,
         "content": "Anesthesiologist airway management ventilation monitoring"}
        for i in range(8)]


class LiveAcceptanceUnitTests(unittest.TestCase):
    @patch("source_retrieval_acceptance_v2.audit_textbook_retrieval")
    @patch("source_retrieval_acceptance_v2.search_passages")
    def test_five_samples_and_owner_isolation(self, search, audit):
        audit.return_value = {"text_search_ready": True, "chapter_filter_ready": False}
        def fake_search(_conn, *, owner_uid, textbook_id, query, page_start=None,
                        page_end=None, limit=20):
            if owner_uid != OWNER: return []
            return [{"chunk_index": p["chunk_index"],
                     "page_start": p["page_start"], "page_end": p["page_end"]}
                    for p in ROWS if p["page_start"] == page_start]
        search.side_effect = fake_search
        result = verify_retrieval_against_extraction(
            object(), owner_uid=OWNER, textbook_id=BOOK, fresh_passages=ROWS)
        self.assertEqual(result["matched_sample_count"], 5)
        self.assertTrue(result["cross_owner_denial_checked"])
        self.assertFalse(result["printed_citations_verified"])

    @patch("source_retrieval_acceptance_v2.audit_textbook_retrieval")
    @patch("source_retrieval_acceptance_v2.search_passages")
    def test_missing_matches_fail_closed(self, search, audit):
        audit.return_value = {"text_search_ready": True, "chapter_filter_ready": False}
        search.return_value = []
        with self.assertRaisesRegex(ValueError, "retrieval accuracy failed"):
            verify_retrieval_against_extraction(
                object(), owner_uid=OWNER, textbook_id=BOOK, fresh_passages=ROWS)

    @patch("source_retrieval_acceptance_v2.audit_textbook_retrieval")
    @patch("source_retrieval_acceptance_v2.search_passages")
    def test_cross_owner_leak_fails_closed(self, search, audit):
        audit.return_value = {"text_search_ready": True, "chapter_filter_ready": False}
        def fake_search(_conn, *, owner_uid, textbook_id, query, page_start=None,
                        page_end=None, limit=20):
            if page_start is None: return [{"chunk_index": 0}]
            return [{"chunk_index": p["chunk_index"], "page_start": p["page_start"],
                     "page_end": p["page_end"]} for p in ROWS
                    if p["page_start"] == page_start]
        search.side_effect = fake_search
        with self.assertRaisesRegex(ValueError, "Cross-owner"):
            verify_retrieval_against_extraction(
                object(), owner_uid=OWNER, textbook_id=BOOK, fresh_passages=ROWS)


if __name__ == "__main__":
    unittest.main()
