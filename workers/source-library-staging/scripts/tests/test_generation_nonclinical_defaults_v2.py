"""Offline regression: placeholders cannot conceal missing clinical evidence."""
import unittest
from item_generation_runner_v2 import _complete_nonclinical_schema_fields


class NonclinicalDefaultsTests(unittest.TestCase):
    def test_missing_mc_unused_fields_and_unverified_metadata(self):
        item = _complete_nonclinical_schema_fields({"format": "MC", "stem": "Sample"})
        self.assertIsNone(item["sa"])
        self.assertIsNone(item["dd"])
        self.assertIsNone(item["hs"])
        self.assertEqual(item["audit"], [])
        self.assertEqual(item["self_check"], {})
        self.assertEqual(item["stats"], {})
        self.assertNotIn("evidence", item)
        self.assertNotIn("distractor_evidence", item)

    def test_preserves_actual_format_fields_and_existing_metadata(self):
        original = {"format": "SA", "sa": {"answer": 4},
                    "audit": [{"result": "pending"}],
                    "self_check": {"reviewed": False}, "stats": {"attempts": 0}}
        item = _complete_nonclinical_schema_fields(original)
        self.assertEqual(item["sa"], {"answer": 4})
        self.assertEqual(item["audit"], original["audit"])
        self.assertEqual(item["self_check"], original["self_check"])
        self.assertEqual(item["stats"], original["stats"])
        self.assertIsNone(item["dd"])
        self.assertIsNone(item["hs"])

    def test_does_not_replace_invalid_or_unverified_clinical_fields(self):
        original = {"format": "MC", "evidence": [{"passage_id": "unknown"}],
                    "distractor_evidence": None, "audit": "invalid",
                    "self_check": [], "stats": False}
        item = _complete_nonclinical_schema_fields(original)
        self.assertEqual(item["evidence"], original["evidence"])
        self.assertIsNone(item["distractor_evidence"])
        self.assertEqual(item["audit"], "invalid")
        self.assertEqual(item["self_check"], [])
        self.assertIs(item["stats"], False)


if __name__ == "__main__":
    unittest.main()
