"""Chapter review must reject invalid input before accessing R2."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("review_r2_chapters", ROOT / "review_r2_chapters.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReviewAuditTests(unittest.TestCase):
    def test_invalid_owner(self):
        with self.assertRaisesRegex(ValueError, "owner UUID"):
            module.audit("invalid", "invalid/book.pdf", None)

    def test_rejects_wrong_owner_key(self):
        with self.assertRaisesRegex(ValueError, "owner-scoped"):
            module.audit("895ed357-27c3-4d4b-a98a-77b0de20760c",
                         "c003287a-10ce-4cc9-926e-ef7c3a162a26/book.pdf", None)

    def test_rejects_non_pdf(self):
        owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
        with self.assertRaisesRegex(ValueError, "owner-scoped"):
            module.audit(owner, owner + "/notes.txt", None)


if __name__ == "__main__":
    unittest.main()
