"""Review-only chapter proposals must never be treated as verified sections."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("propose_chapters", ROOT / "propose_chapters.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ChapterProposalTests(unittest.TestCase):
    def test_detects_chapter_at_page_start_only(self):
        pages = [
            {"pdf_page": 1, "text": "Chapter 1: Introduction\nDetails"},
            {"pdf_page": 2, "text": "The author refers to Chapter 2 in prose."},
            {"pdf_page": 10, "text": "CHAPTER 2 Airway Assessment\nDetails"},
        ]
        proposals = module.propose(pages)
        self.assertEqual([p["pdf_page"] for p in proposals], [1, 10])
        self.assertTrue(all(p["review_required"] for p in proposals))
        self.assertTrue(all(p["source"] == "unverified_text_heuristic" for p in proposals))

    def test_no_false_verified_sections_without_headings(self):
        self.assertEqual(module.propose([{"pdf_page": 1, "text": "Preface\nContents"}]), [])


if __name__ == "__main__":
    unittest.main()
