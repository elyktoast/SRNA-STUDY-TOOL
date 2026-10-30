"""Local review HTML must escape textbook text and never approve sections."""
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

path = Path(__file__).resolve().parents[1] / "chapter_review_export.py"
spec = importlib.util.spec_from_file_location("chapter_review_export", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class ExportTests(unittest.TestCase):
    def test_escapes_untrusted_pdf_heading(self):
        groups = [{"first_page": 2, "last_page": 2,
                   "candidates": [{"pdf_page": 2, "detector": "layout",
                                   "heading": '<script>alert("x")</script>'}]}]
        output = module.render_review_html(groups, 'a&b.pdf')
        self.assertNotIn("<script>", output)
        self.assertIn("&lt;script&gt;", output)
        self.assertIn("a&amp;b.pdf", output)
        self.assertIn("Selection does not save", output)
        self.assertIn("Export review decisions (JSON)", output)
        self.assertIn("chapter-review-decisions.json", output)
        self.assertIn("schema_version:2", output)
        self.assertIn("review_fingerprint:", output)

    def test_never_overwrites_existing_review(self):
        with TemporaryDirectory() as temp:
            target = Path(temp) / "review.html"
            module.write_local_review([], "a.pdf", target)
            with self.assertRaises(FileExistsError):
                module.write_local_review([], "a.pdf", target)

if __name__ == "__main__":
    unittest.main()
