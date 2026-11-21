"""Real PDF regressions for the opt-in paragraph-preserving extraction candidate."""
import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path

import fitz
from extract_textbook import extract, page_text


class BlockReadingOrderTests(unittest.TestCase):
    def make_page(self):
        doc = fitz.open()
        page = doc.new_page(width=600, height=800)
        page.insert_text((40, 70), 'Left topic begins here.\nLeft topic continues here.')
        page.insert_text((330, 70), 'Right topic begins here.\nRight topic continues here.')
        return doc, page

    def test_parallel_columns_keep_each_paragraph_together(self):
        doc, page = self.make_page()
        self.addCleanup(doc.close)
        legacy = page_text(page)
        candidate = page_text(page, reading_order='blocks')
        self.assertNotIn('Left topic begins here.\nLeft topic continues here.', legacy)
        self.assertIn('Left topic begins here.\nLeft topic continues here.', candidate)
        self.assertIn('Right topic begins here.\nRight topic continues here.', candidate)
        self.assertEqual(Counter(candidate.split()), Counter(legacy.split()))

    def test_existing_textpage_can_supply_both_reading_modes(self):
        doc, page = self.make_page()
        self.addCleanup(doc.close)
        textpage = page.get_textpage()
        self.assertEqual(page_text(page, reading_order='blocks'),
                         page_text(page, reading_order='blocks', textpage=textpage))

    def test_single_column_text_and_blank_page_do_not_lose_words(self):
        with fitz.open() as doc:
            page = doc.new_page()
            self.assertEqual(page_text(page, reading_order='blocks'), '')
            page.insert_text((40, 70), 'A complete paragraph.\nIt continues on the next line.')
            self.assertEqual(page_text(page, reading_order='blocks'), page_text(page))

    def test_opt_in_is_recorded_without_certifying_reading_order_or_citations(self):
        doc, _ = self.make_page()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'columns.pdf'
            doc.save(path)
            doc.close()
            owner = '895ed357-27c3-4d4b-a98a-77b0de20760c'
            for mode in ('legacy', 'blocks'):
                out = Path(temp) / mode
                manifest = extract(path, out, owner, owner+'/columns.pdf', reading_order=mode)
                self.assertEqual(manifest['text_reading_order'], mode)
                self.assertFalse(manifest['reading_order_verified'])
                self.assertFalse(manifest['citation_verified'])
                passages = [json.loads(line) for line in (out/'passages.jsonl').read_text().splitlines()]
                self.assertTrue(all(p['page_start'] == 1 and p['page_end'] == 1 for p in passages))
                if mode == 'blocks':
                    self.assertIn('Left topic begins here.\nLeft topic continues here.', passages[0]['content'])

    def test_invalid_mode_fails_before_pdf_access(self):
        with self.assertRaisesRegex(ValueError, 'reading order'):
            extract(Path('/nonexistent.pdf'), Path('/nonexistent-output'), '', '', reading_order='guess')


if __name__ == '__main__':
    unittest.main()
