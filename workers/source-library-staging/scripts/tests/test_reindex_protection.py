import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_extraction import assert_safe_reindex

class ReindexProtectionTests(unittest.TestCase):
    def test_empty_index(self):
        assert_safe_reindex(0)

    def test_existing_sections(self):
        with self.assertRaises(ValueError):
            assert_safe_reindex(2)

    def test_invalid_count(self):
        with self.assertRaises(ValueError):
            assert_safe_reindex(-1)
