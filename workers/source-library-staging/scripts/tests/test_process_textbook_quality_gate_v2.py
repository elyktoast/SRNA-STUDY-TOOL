import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from process_textbook import process, ReviewRequiredError
from source_review_authorization_v2 import TrustedReviewApproval


class ProcessQualityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / "book.pdf"
        self.pdf.write_bytes(b"%PDF-mock")
        self.owner = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
        self.key = self.owner + "/book.pdf"
        self.digest = hashlib.sha256(self.pdf.read_bytes()).hexdigest()
        self.manifest = {
            "pdf_page_count": 4, "passage_count": 2, "sha256": self.digest,
            "owner_uid": self.owner, "r2_key": self.key,
            "requires_ocr_review": True, "low_text_pages": [2],
            "ocr_failed_pages": [2], "ocr_attempted": True, "ocr_pages": [],
            "status": "extracted_not_indexed", "citation_verified": False,
            "page_numbering": "physical_pdf_page_1_based"
        }

    def fake_database(self):
        connection = MagicMock()
        connection.__enter__.return_value = connection
        return SimpleNamespace(connect=MagicMock(return_value=connection))

    def test_dry_run_and_unattested_file_do_not_authorize_indexing(self):
        with patch("process_textbook.extract", return_value=self.manifest), patch(
                "process_textbook.validate", return_value=self.manifest):
            result = process(self.pdf, self.root / "index", self.owner, self.key, apply=False)
            self.assertEqual(result["extraction_quality"]["unresolved_pdf_pages"], [2])
            self.assertFalse(result["indexed"])
            self.assertFalse(result["citation_verified"])
            with self.assertRaisesRegex(ValueError, "not authenticated"):
                process(self.pdf, self.root / "index", self.owner, self.key,
                        apply=True, page_review_file=self.root / "untrusted.json")
            with self.assertRaisesRegex(ValueError, "Unattested page flags"):
                process(self.pdf, self.root / "index", self.owner, self.key,
                        apply=True, reviewed_pages=[2])

    def test_protected_approval_must_be_complete_and_admin_role_active(self):
        psycopg = self.fake_database()
        with patch("process_textbook.extract", return_value=self.manifest), patch(
                "process_textbook.validate", return_value=self.manifest), patch.dict(
                sys.modules, {"psycopg": psycopg}), patch.dict(
                "os.environ", {"DATABASE_URL": "test-database"}, clear=False), patch(
                "process_textbook.ProtectedReviewerRoleStore") as role, patch(
                "process_textbook.load_approved_pages") as loader, patch(
                "process_textbook.import_passages", return_value="book-id") as importer:
            role.return_value.is_active_admin.return_value = False
            with self.assertRaisesRegex(ValueError, "operator-admin"):
                process(self.pdf, self.root / "index", self.owner, self.key, apply=True)
            loader.assert_not_called()
            importer.assert_not_called()

            role.return_value.is_active_admin.return_value = True
            loader.return_value = TrustedReviewApproval(
                self.owner, self.digest, self.key, self.owner, frozenset())
            with self.assertRaises(ReviewRequiredError) as ctx:
                process(self.pdf, self.root / "index", self.owner, self.key, apply=True)
            self.assertEqual(ctx.exception.diagnostics["extraction_quality"]["unresolved_pdf_pages"], [2])
            importer.assert_not_called()

            loader.return_value = TrustedReviewApproval(
                self.owner, self.digest, self.key, self.owner, frozenset({2}))
            result = process(self.pdf, self.root / "index", self.owner, self.key, apply=True)
            self.assertTrue(result["indexed"])
            self.assertEqual(result["textbook_id"], "book-id")
            self.assertEqual(result["extraction_quality"]["reviewed_pdf_pages"], [2])
            self.assertEqual(result["extraction_quality"]["unresolved_pdf_pages"], [])
            self.assertEqual(result["review_required_pages"], [])
            importer.assert_called_once()
            self.assertEqual(importer.call_args.kwargs["authenticated_reviewer_uid"], self.owner)
            self.assertIs(importer.call_args.kwargs["reviewer_is_admin"], True)


if __name__ == "__main__":
    unittest.main()
