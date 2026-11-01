import unittest
from source_chapter_boundaries_v2 import validate_chapter_boundaries, assign_passages_to_chapters


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

    def test_invalid_passage_pages_are_rejected(self):
        for passage in [{"page_start": 0, "page_end": 1},
                        {"page_start": 3, "page_end": 31},
                        {"page_start": 10, "page_end": 9},
                        {"page_start": True, "page_end": 10}]:
            with self.subTest(passage=passage), self.assertRaises(ValueError):
                assign_passages_to_chapters([passage], self.chapters, pdf_page_count=30)


if __name__ == "__main__":
    unittest.main()
