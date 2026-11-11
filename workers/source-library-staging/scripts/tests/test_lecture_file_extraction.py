import io
import unittest
from unittest.mock import patch
from lecture_file_extraction import extract_lecture

class LectureFileExtractionTests(unittest.TestCase):
    def test_rejects_wrong_file_signatures_and_unsupported_formats(self):
        for name, data in [('slides.pdf', b'not a pdf'), ('slides.pptx', b'not a zip'),
                           ('slides.ppt', b'legacy'), ('slides.docx', b'PKxx')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                extract_lecture(data, name)

    def test_pdf_text_and_image_only_pages(self):
        try:
            import fitz
        except ImportError:
            self.skipTest('PyMuPDF not installed')
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((70, 70), 'Anesthesia pharmacology lecture')
        doc.new_page()
        result = extract_lecture(doc.tobytes(), 'Lecture.PDF')
        self.assertEqual(result['page_count'], 2)
        self.assertEqual(result['review_pages'], [2])
        self.assertIn('Anesthesia pharmacology', result['pages'][0]['text'])
        self.assertFalse(result['extraction_complete'])
        self.assertFalse(result['database_writes'])

    def test_pptx_text_table_and_empty_slide(self):
        try:
            from pptx import Presentation
        except ImportError:
            self.skipTest('python-pptx not installed')
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = 'Ventilation'
        table = slide.shapes.add_table(1, 2, 0, 1000000, 4000000, 800000).table
        table.cell(0, 0).text = 'PEEP'
        table.cell(0, 1).text = '5'
        prs.slides.add_slide(prs.slide_layouts[6])
        stream = io.BytesIO()
        prs.save(stream)
        result = extract_lecture(stream.getvalue(), 'lecture.pptx')
        self.assertEqual(result['review_pages'], [2])
        self.assertIn('PEEP | 5', result['pages'][0]['text'])

    def test_pptx_image_is_held_even_with_slide_text(self):
        try:
            from pptx import Presentation
            import fitz
        except ImportError:
            self.skipTest('Presentation or PyMuPDF dependency unavailable')
        prs = Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[5])
        slide.shapes.title.text = 'Hemodynamic waveform'
        doc = fitz.open()
        page = doc.new_page(width=100, height=100)
        page.insert_text((10, 50), 'MAP')
        image = page.get_pixmap().tobytes('png')
        slide.shapes.add_picture(io.BytesIO(image), 0, 1200000, width=1000000)
        output = io.BytesIO()
        prs.save(output)
        result = extract_lecture(output.getvalue(), 'waveform.pptx')
        self.assertEqual(result['review_pages'], [1])
        self.assertEqual(result['pages'][0]['image_count'], 1)
        self.assertIn('Hemodynamic waveform', result['pages'][0]['text'])

if __name__ == '__main__':
    unittest.main()
