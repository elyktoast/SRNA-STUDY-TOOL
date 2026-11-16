import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

import fitz
from audit_pdf_reading_order_v2 import audit, compare_page

OWNER = '895ed357-27c3-4d4b-a98a-77b0de20760c'
BOOK = '395ed357-27c3-4d4b-a98a-77b0de20760c'


class ReadingOrderAuditTests(unittest.TestCase):
    def test_parallel_paragraph_probe_improves_without_disclosing_text(self):
        with fitz.open() as doc:
            page = doc.new_page(width=600, height=800)
            page.insert_text((40,70), 'Private left sentence.\nPrivate left continuation.')
            page.insert_text((330,70), 'Separate right sentence.\nSeparate right continuation.')
            result = compare_page(page, {'continuity': 'Private left sentence. Private left continuation.'})
        self.assertFalse(result['legacy_continuity_checks']['continuity'])
        self.assertTrue(result['block_continuity_checks']['continuity'])
        self.assertTrue(result['non_whitespace_characters_preserved'])
        self.assertTrue(result['block_matches_source_glyphs'])
        self.assertTrue(result['legacy_matches_source_glyphs'])
        self.assertGreater(result['legacy_wide_gap_rows'], 0)
        self.assertNotIn('Private', json.dumps(result))

    def test_failed_probe_is_reported_instead_of_inventing_support(self):
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((40,70), 'A short single paragraph.')
            result = compare_page(page, {'missing': 'Absent evidence'})
        self.assertFalse(result['block_continuity_checks']['missing'])

    def test_candidate_character_loss_fails_independent_raw_glyph_inventory(self):
        with fitz.open() as doc:
            page = doc.new_page()
            page.insert_text((40,70), 'Original source text.')
            with patch('audit_pdf_reading_order_v2.page_text',
                       side_effect=['Original source text.', 'Original source tex.']):
                result = compare_page(page)
        self.assertTrue(result['legacy_matches_source_glyphs'])
        self.assertFalse(result['block_matches_source_glyphs'])
        self.assertEqual(result['legacy_only_codepoints'], {'U+0074':1})

    def test_missing_provenance_blocks_source_read(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchone.return_value = None
        with patch('audit_pdf_reading_order_v2.verified_staging_pdf_file') as source:
            with self.assertRaisesRegex(ValueError, 'source provenance'):
                audit(conn, object(), owner_uid=OWNER, textbook_id=BOOK, pages=[1])
        source.assert_not_called()
        self.assertEqual(conn.cursor.return_value.__enter__.return_value.execute.call_args.args[1],
                         (OWNER, BOOK))

    def test_invalid_pages_fail_before_database_and_storage_access(self):
        for pages in ([], [0], [True], [1,1], list(range(1,22))):
            conn = MagicMock()
            with self.subTest(pages=pages), self.assertRaises(ValueError):
                audit(conn, object(), owner_uid=OWNER, textbook_id=BOOK, pages=pages)
            conn.cursor.assert_not_called()

    def test_verified_original_is_only_read_and_private_path_is_not_reported(self):
        with tempfile.TemporaryDirectory() as temp:
            pdf = Path(temp)/'private-source.pdf'
            with fitz.open() as doc:
                doc.new_page().insert_text((40,70),'Private textbook contents.')
                doc.save(pdf)
            digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
            conn = MagicMock()
            conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
                'book.pdf', OWNER+'/book.pdf', pdf.stat().st_size, 1, digest)
            with patch('audit_pdf_reading_order_v2.verified_staging_pdf_file') as source:
                source.return_value.__enter__.return_value = str(pdf)
                result = audit(conn, object(), owner_uid=OWNER, textbook_id=BOOK, pages=[1])
            source.assert_called_once()
            self.assertEqual(source.call_args.kwargs['expected_sha256'], digest)
            self.assertTrue(result['candidate_checks_passed'])
            for key in ('database_writes','r2_writes','provider_calls','index_replaced',
                        'clinical_accuracy_verified','full_reading_order_verified'):
                self.assertFalse(result[key])
            self.assertNotIn(str(pdf), json.dumps(result))
            self.assertNotIn('Private textbook contents.', json.dumps(result))
            conn.commit.assert_not_called()

    def test_page_outside_provenance_fails_before_storage(self):
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchone.return_value = (
            'book.pdf', OWNER+'/book.pdf', 100, 1, 'a'*64)
        with patch('audit_pdf_reading_order_v2.verified_staging_pdf_file') as source:
            with self.assertRaisesRegex(ValueError,'outside'):
                audit(conn, object(), owner_uid=OWNER, textbook_id=BOOK, pages=[2])
        source.assert_not_called()
