"""Chapter candidate review must preserve evidence without approving sections."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "chapter_review.py"
spec = importlib.util.spec_from_file_location("chapter_review", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ReviewGroupingTests(unittest.TestCase):
    def test_adjacent_candidates_grouped_without_discarding_evidence(self):
        text = [{"pdf_page": 24, "heading": "Chapter 1 Introduction"}]
        layout = [{"pdf_page": 23, "heading": "Introduction"},
                  {"pdf_page": 24, "heading": "Chapter 1 Introduction"},
                  {"pdf_page": 65, "heading": "Airway"}]
        groups = module.review_groups(text, layout)
        self.assertEqual(len(groups), 2)
        self.assertEqual([len(g["candidates"]) for g in groups], [3, 1])
        self.assertEqual(groups[0]["detectors"], ["layout", "text"])
        summary = module.public_review_summary(groups)
        self.assertEqual(summary["review_group_page_ranges"], [[23, 24], [65, 65]])
        self.assertEqual(summary["sections_approved"], 0)
        self.assertNotIn("Introduction", str(summary))

    def test_rejects_invalid_pages(self):
        with self.assertRaises(ValueError):
            module.review_groups([{"pdf_page": 0, "heading": "A"}], [])

if __name__ == "__main__":
    unittest.main()
