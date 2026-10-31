"""Full legacy passage comparison must fail closed on differences."""
import json
import tempfile
import unittest
from pathlib import Path

from compare_legacy_extraction import compare_passages


class LegacyComparisonTests(unittest.TestCase):
    def test_all_fields_must_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            passages = [
                {"chunk_index": 0, "page_start": 1, "page_end": 1, "content": "first"},
                {"chunk_index": 1, "page_start": 2, "page_end": 2, "content": "second"},
            ]
            (folder / "passages.jsonl").write_text(
                "".join(json.dumps(x) + "\n" for x in passages))
            rows = [(0, 1, 1, "first"), (1, 2, 2, "second")]
            self.assertTrue(compare_passages(folder, rows)["matched"])
            self.assertFalse(compare_passages(folder, rows[:1])["matched"])
            self.assertEqual(compare_passages(folder, [(0, 1, 1, "first"), (1, 2, 2, "changed")])["first_mismatch_chunk"], 1)
            self.assertFalse(compare_passages(folder, [(0, 1, 1, "first"), (1, 3, 3, "second")])["matched"])
