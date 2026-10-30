"""Run: python -m unittest discover -s workers/source-library-staging/scripts/tests -v"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("import_extraction", ROOT / "import_extraction.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ImportValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
        self.manifest = {
            "schema_version": 1, "status": "extracted_not_indexed",
            "citation_verified": False, "owner_uid": self.owner,
            "r2_key": self.owner + "/sample.pdf", "filename": "sample.pdf",
            "size_bytes": 1024, "sha256": "a" * 64, "pdf_page_count": 2,
            "passage_count": 2, "requires_ocr_review": False,
        }
        self.passages = [
            {"chunk_index": 0, "page_start": 1, "page_end": 1, "content": "Airway anatomy"},
            {"chunk_index": 1, "page_start": 2, "page_end": 2, "content": "Volatile anesthetics"},
        ]
        self.write()

    def write(self):
        (self.folder / "manifest.json").write_text(json.dumps(self.manifest), encoding="utf-8")
        (self.folder / "passages.jsonl").write_text(
            "".join(json.dumps(x) + "\n" for x in self.passages), encoding="utf-8")

    def test_valid(self):
        self.assertEqual(module.validate(self.folder)["passage_count"], 2)

    def test_valid_bookmark_sections(self):
        self.manifest["section_count"] = 2
        self.write()
        (self.folder / "sections.jsonl").write_text(
            "".join(json.dumps(s) + "\n" for s in [
                {"level": 1, "heading": "Airway", "start_page": 1, "source": "pdf_bookmark"},
                {"level": 1, "heading": "Pharmacology", "start_page": 2, "source": "pdf_bookmark"},
            ]), encoding="utf-8")
        self.assertEqual(module.validate(self.folder)["section_count"], 2)

    def test_rejects_section_outside_pdf(self):
        self.manifest["section_count"] = 1
        self.write()
        (self.folder / "sections.jsonl").write_text(
            json.dumps({"level": 1, "heading": "Invalid", "start_page": 3,
                        "source": "pdf_bookmark"}) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Invalid PDF bookmark section"):
            module.validate(self.folder)

    def test_rejects_missing_section_records(self):
        self.manifest["section_count"] = 1
        self.write()
        with self.assertRaisesRegex(ValueError, "section count mismatch"):
            module.validate(self.folder)

    def test_rejects_mismatched_count(self):
        self.manifest["passage_count"] = 3
        self.write()
        with self.assertRaisesRegex(ValueError, "count mismatch"):
            module.validate(self.folder)

    def test_rejects_page_outside_pdf(self):
        self.passages[1]["page_end"] = 3
        self.write()
        with self.assertRaisesRegex(ValueError, "outside document"):
            module.validate(self.folder)

    def test_rejects_noncontiguous_chunks(self):
        self.passages[1]["chunk_index"] = 4
        self.write()
        with self.assertRaisesRegex(ValueError, "contiguous"):
            module.validate(self.folder)

    def test_rejects_claimed_verified_citations(self):
        self.manifest["citation_verified"] = True
        self.write()
        with self.assertRaisesRegex(ValueError, "citation verification"):
            module.validate(self.folder)

    def test_rejects_nonhex_digest(self):
        self.manifest["sha256"] = "z" * 64
        self.write()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            module.validate(self.folder)

    def test_rejects_malformed_owner(self):
        self.manifest["owner_uid"] = "not-a-uuid"
        self.manifest["r2_key"] = "not-a-uuid/sample.pdf"
        self.write()
        with self.assertRaisesRegex(ValueError, "owner/key"):
            module.validate(self.folder)

    def test_rejects_missing_digest(self):
        del self.manifest["sha256"]
        self.write()
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            module.validate(self.folder)

    def test_rejects_empty_extraction(self):
        self.passages = []
        self.manifest["passage_count"] = 0
        self.write()
        with self.assertRaisesRegex(ValueError, "No searchable passages"):
            module.validate(self.folder)

    def test_rejects_cross_owner_key(self):
        self.manifest["r2_key"] = "other/sample.pdf"
        self.write()
        with self.assertRaisesRegex(ValueError, "owner/key"):
            module.validate(self.folder)


if __name__ == "__main__":
    unittest.main()
