import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from source_review_queue_publish_v2 import prepare_queue_artifacts

UID = "123e4567-e89b-42d3-a456-426614174000"


class PublishPreparationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pdf = self.root / "book.pdf"
        self.pdf.write_bytes(b"%PDF-1.4\nmock content")
        self.manifest = {
            "schema_version": 1, "filename": "book.pdf", "owner_uid": UID,
            "r2_key": UID + "/book.pdf", "size_bytes": self.pdf.stat().st_size,
            "sha256": hashlib.sha256(self.pdf.read_bytes()).hexdigest(),
            "pdf_page_count": 2, "status": "extracted_not_indexed",
            "citation_verified": False, "low_text_pages": [2],
            "low_text_details": [{"pdf_page": 2, "review_category": "ocr_error",
                                  "characters": 0, "ocr_failed": True}],
        }
        self.write_manifest()

    def write_manifest(self):
        (self.root / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")

    def test_preparation_binds_queue_to_original_bytes(self):
        result = prepare_queue_artifacts(self.pdf, self.root)
        self.assertEqual(result["pdf_sha256"], self.manifest["sha256"])
        self.assertEqual(result["queue_r2_key"], UID + "/_review_queues/book.pdf.json")
        self.assertEqual(json.loads(result["queue_json"])["pages"][0]["pdf_page"], 2)
        self.assertFalse(result["approval_enabled"])

    def test_changed_pdf_rejected(self):
        self.pdf.write_bytes(b"%PDF-1.4\nmock contenX")
        with self.assertRaisesRegex(ValueError, "digest mismatch"):
            prepare_queue_artifacts(self.pdf, self.root)

    def test_forged_manifest_or_filename_rejected(self):
        for field, value in (("filename", "other.pdf"), ("r2_key", UID + "/_other/book.pdf"),
                             ("citation_verified", True), ("status", "indexed")):
            with self.subTest(field=field):
                original = self.manifest[field]
                self.manifest[field] = value
                self.write_manifest()
                with self.assertRaises(ValueError):
                    prepare_queue_artifacts(self.pdf, self.root)
                self.manifest[field] = original


if __name__ == "__main__":
    unittest.main()
