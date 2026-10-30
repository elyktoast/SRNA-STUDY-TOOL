"""Exercise the staging importer with a fake transaction and SQL cursor.

No database credentials or external services are required.
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("import_extraction", ROOT / "import_extraction.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Cursor:
    def __init__(self):
        self.executed = []
        self.batches = []
        self.last_id = None
        self.next_section = 0
        self.existing_sections = []
        self.existing_textbook = False
        self.prior_digest = 'a' * 64
        self.duplicate_r2_key = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))
        if "where r2_key=%s for update" in sql:
            self.last_id = "book-id" if self.existing_textbook else None
        elif "select source_sha256 from source_library_staging.source_versions" in sql:
            self.last_id = self.prior_digest
        elif "select r2_key from source_library_staging.source_versions" in sql:
            self.last_id = self.duplicate_r2_key
        elif "insert into source_library_staging.textbooks" in sql:
            self.last_id = "book-id"
        elif "insert into source_library_staging.sections" in sql:
            self.next_section += 1
            self.last_id = f"section-{self.next_section}"

    def fetchall(self):
        return list(self.existing_sections)

    def fetchone(self):
        return (self.last_id,) if self.last_id is not None else None

    def executemany(self, sql, params):
        self.batches.append((sql, list(params)))


class Transaction:
    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class Connection:
    def __init__(self):
        self.cur = Cursor()

    def transaction(self):
        return Transaction()

    def cursor(self):
        return self.cur


class ImportHierarchyTests(unittest.TestCase):
    def test_parent_links_and_passage_section_mapping(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            sections = [
                {"level": 1, "heading": "Airway", "start_page": 1, "source": "pdf_bookmark"},
                {"level": 2, "heading": "Intubation", "start_page": 2, "source": "pdf_bookmark"},
                {"level": 1, "heading": "Pharmacology", "start_page": 3, "source": "pdf_bookmark"},
            ]
            passages = [
                {"chunk_index": i, "page_start": i + 1, "page_end": i + 1,
                 "content": f"passage {i}"} for i in range(3)
            ]
            (folder / "sections.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in sections))
            (folder / "passages.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in passages))
            conn = Connection()
            manifest = {"owner_uid": "895ed357-27c3-4d4b-a98a-77b0de20760c",
                        "r2_key": "895ed357-27c3-4d4b-a98a-77b0de20760c/book.pdf",
                        "filename": "book.pdf", "size_bytes": 1234, "sha256": "a" * 64,
                        "pdf_page_count": 3, "requires_ocr_review": False, "low_text_pages": []}
            self.assertEqual(module.import_passages(folder, manifest, conn), "book-id")
            inserts = [params for sql, params in conn.cur.executed
                       if "insert into source_library_staging.sections" in sql]
            self.assertEqual([x[1] for x in inserts], [None, "section-1", None])
            self.assertEqual([row[1] for row in conn.cur.batches[0][1]],
                             ["section-1", "section-2", "section-3"])
            self.assertTrue(any("status='ready'" in sql for sql, _ in conn.cur.executed))
            protected = Connection()
            protected.cur.existing_sections = [('saved-1', 1), ('saved-2', 2)]
            protected.cur.existing_textbook = True
            self.assertEqual(module.import_passages(folder, manifest, protected), "book-id")
            self.assertFalse(any(
                'delete from source_library_staging.sections' in sql
                or 'insert into source_library_staging.sections' in sql
                for sql, _ in protected.cur.executed
            ))
            self.assertEqual([row[1] for row in protected.cur.batches[0][1]],
                             ['saved-1', 'saved-2', 'saved-2'])
            invalid = Connection()
            invalid.cur.existing_textbook = True
            invalid.cur.existing_sections = [('saved-1', None)]
            with self.assertRaisesRegex(ValueError, "invalid start page"):
                module.import_passages(folder, manifest, invalid)
            self.assertFalse(any('delete from' in sql for sql, _ in invalid.cur.executed))
            out_of_range = Connection()
            out_of_range.cur.existing_textbook = True
            out_of_range.cur.existing_sections = [('saved-1', 4)]
            with self.assertRaisesRegex(ValueError, "invalid start page"):
                module.import_passages(folder, manifest, out_of_range)
            self.assertFalse(any('delete from' in sql for sql, _ in out_of_range.cur.executed))
            legacy = Connection()
            legacy.cur.existing_textbook = True
            legacy.cur.prior_digest = None
            with self.assertRaisesRegex(ValueError, "fingerprint is unknown"):
                module.import_passages(folder, manifest, legacy)
            self.assertFalse(any(
                "delete from source_library_staging.passages" in sql
                for sql, _ in legacy.cur.executed
            ))
            changed = Connection()
            changed.cur.existing_textbook = True
            changed.cur.prior_digest = 'b' * 64
            with self.assertRaisesRegex(ValueError, "source PDF changed"):
                module.import_passages(folder, manifest, changed)
            self.assertFalse(any('delete from' in sql for sql, _ in changed.cur.executed))
            duplicate = Connection()
            duplicate.cur.duplicate_r2_key = manifest["owner_uid"] + "/another.pdf"
            with self.assertRaisesRegex(ValueError, "Duplicate textbook content"):
                module.import_passages(folder, manifest, duplicate)
            self.assertFalse(any(
                "insert into source_library_staging.textbooks" in sql
                for sql, _ in duplicate.cur.executed
            ))


if __name__ == "__main__":
    unittest.main()
