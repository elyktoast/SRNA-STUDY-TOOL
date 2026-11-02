"""Regression checks for source fingerprint replacement policy."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from import_extraction import assert_safe_reindex, validate_source_replacement


class SourceVersionGuardTests(unittest.TestCase):
    def test_first_import(self):
        validate_source_replacement(False, None, "a" * 64)

    def test_same_digest(self):
        validate_source_replacement(True, "a" * 64, "a" * 64)

    def test_changed_digest(self):
        with self.assertRaisesRegex(ValueError, "source PDF changed"):
            validate_source_replacement(True, "a" * 64, "b" * 64)

    def test_unknown_legacy_digest(self):
        with self.assertRaisesRegex(ValueError, "fingerprint is unknown"):
            validate_source_replacement(True, None, "a" * 64)

    def test_existing_chapters_still_blocked(self):
        with self.assertRaises(ValueError):
            assert_safe_reindex(1)


if __name__ == "__main__":
    unittest.main()
