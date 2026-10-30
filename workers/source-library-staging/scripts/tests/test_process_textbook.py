"""End-to-end local PDF -> manifest -> passage validation smoke test.

No database connection, R2 access, or secrets. Run with:
python -m unittest discover -s workers/source-library-staging/scripts/tests -v
"""
import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location("process_textbook", ROOT / "process_textbook.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        try:
            import fitz
        except ImportError:
            self.skipTest("pymupdf not installed")
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.pdf = self.folder / "sample.pdf"
        document = fitz.open()
        for content in (
            "Endotracheal intubation requires confirmation of ventilation.",
            "Volatile anesthetic uptake depends on ventilation and blood solubility.",
        ):
            page = document.new_page()
            page.insert_text((72, 72), content)
        document.save(self.pdf)
        document.close()
        self.owner = "895ed357-27c3-4d4b-a98a-77b0de20760c"
        self.key = self.owner + "/sample.pdf"

    def test_dry_run_pipeline_and_page_mapping(self):
        out = self.folder / "index"
        result = module.process(self.pdf, out, self.owner, self.key, apply=False)
        self.assertEqual(result["pdf_pages"], 2)
        self.assertEqual(result["passages"], 2)
        self.assertFalse(result["indexed"])
        self.assertFalse(result["citation_verified"])
        self.assertRegex(result["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(result["source_sha256"], manifest["sha256"])
        manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["status"], "extracted_not_indexed")
        rows = [json.loads(line) for line in (out / "passages.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(r["page_start"], r["page_end"]) for r in rows], [(1, 1), (2, 2)])
        self.assertIn("intubation", rows[0]["content"])
        self.assertIn("Volatile", rows[1]["content"])

    def test_bookmark_hierarchy_survives_complete_dry_run(self):
        import fitz
        document = fitz.open(self.pdf)
        document.set_toc([[1, "Airway", 1], [2, "Tube confirmation", 1],
                          [1, "Pharmacology", 2]])
        source = self.folder / "chaptered.pdf"
        document.save(source)
        document.close()
        out = self.folder / "chapter-index"
        result = module.process(source, out, self.owner,
                                self.owner + "/chaptered.pdf")
        self.assertEqual(result["passages"], 2)
        from import_extraction import validate
        manifest = validate(out)
        self.assertEqual(manifest["section_count"], 3)
        sections = [json.loads(line) for line in
                    (out / "sections.jsonl").read_text(encoding="utf-8").splitlines()]
        self.assertEqual([(s["level"], s["start_page"]) for s in sections],
                         [(1, 1), (2, 1), (1, 2)])
        self.assertEqual([s["heading"] for s in sections],
                         ["Airway", "Tube confirmation", "Pharmacology"])
        self.assertFalse(manifest["citation_verified"])

    def test_r2_digest_mismatch_rejected_before_database_import(self):
        with patch.object(module, "import_passages") as importer:
            with self.assertRaisesRegex(ValueError, "differs from original R2"):
                module.process(self.pdf, self.folder / "index", self.owner, self.key,
                               apply=True, expected_sha256="0" * 64)
            importer.assert_not_called()

    def test_source_mutation_after_extraction_is_rejected(self):
        original_extract = module.extract

        def mutate_source(pdf, out, owner_uid, r2_key, ocr=False):
            result = original_extract(pdf, out, owner_uid, r2_key, ocr=ocr)
            with pdf.open("ab") as handle:
                handle.write(b"changed after extraction")
            return result

        with patch.object(module, "extract", side_effect=mutate_source):
            with self.assertRaisesRegex(ValueError, "changed after extraction"):
                module.process(self.pdf, self.folder / "index", self.owner, self.key)

    def test_invalid_owner_rejected_before_index(self):
        with self.assertRaisesRegex(ValueError, "prefix"):
            module.process(self.pdf, self.folder / "index", self.owner, "wrong/sample.pdf")
        self.assertFalse((self.folder / "index" / "manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
