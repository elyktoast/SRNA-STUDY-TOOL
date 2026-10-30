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
        self.existing_sections = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, params):
        self.executed.append((sql, params))
        if "insert into source_library_staging.textbooks" in sql:
            self.last_id = "book-id"
        elif "select count(*) from source_library_staging.sections" in sql:
            self.last_id = self.existing_sections
        elif "insert into source_library_staging.sections" in sql:
            self.next_section += 1
            self.last_id = f"section-{self.next_section}"

    def fetchone(self):
        return (self.last_id,)

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
                        "filename": "book.pdf", "size_bytes": 1234,
                        "pdf_page_count": 3, "requires_ocr_review": False, "low_text_pages": []}
            self.assertEqual(module.import_passages(folder, manifest, conn), "book-id")
            inserts = [params for sql, params in conn.cur.executed
                       if "insert into source_library_staging.sections" in sql]
            self.assertEqual([x[1] for x in inserts], [None, "section-1", None])
            self.assertEqual([row[1] for row in conn.cur.batches[0][1]],
                             ["section-1", "section-2", "section-3"])
            self.assertTrue(any("status='ready'" in sql for sql, _ in conn.cur.executed))


if __name__ == "__main__":
    unittest.main()
