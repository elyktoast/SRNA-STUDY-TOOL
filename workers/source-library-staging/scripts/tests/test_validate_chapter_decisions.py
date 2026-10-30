import importlib.util
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
path = Path(__file__).resolve().parents[1] / "validate_chapter_decisions.py"
spec = importlib.util.spec_from_file_location("validate_chapter_decisions", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
from chapter_review import review_fingerprint

GROUPS = [{"first_page": 20, "last_page": 24}, {"first_page": 65, "last_page": 65}]
def packet():
    return {"schema_version": 2, "review_fingerprint": review_fingerprint(GROUPS), "decisions": [
        {"group": 1, "decision": "Chapter", "notes": ""},
        {"group": 2, "decision": "Reject", "notes": "running header"}]}

class DecisionValidationTests(unittest.TestCase):
    def test_valid_packet_remains_unapproved(self):
        result = mod.validate_decisions(packet(), GROUPS)
        self.assertEqual(result["status"], "validated_unapproved")
        self.assertEqual(result["sections_approved"], 0)
        self.assertFalse(result["database_written"])
        self.assertEqual(result["decisions"][0]["page_range"], [20, 24])

    def test_stale_review_fingerprint_rejected(self):
        data = packet()
        data["review_fingerprint"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
            mod.validate_decisions(data, GROUPS)

    def test_missing_group_rejected(self):
        data = packet()
        data["decisions"].pop()
        with self.assertRaises(ValueError):
            mod.validate_decisions(data, GROUPS)

    def test_duplicate_group_rejected(self):
        data = packet()
        data["decisions"][1]["group"] = 1
        with self.assertRaises(ValueError):
            mod.validate_decisions(data, GROUPS)

    def test_invalid_choice_rejected(self):
        data = packet()
        data["decisions"][0]["decision"] = "Approved"
        with self.assertRaises(ValueError):
            mod.validate_decisions(data, GROUPS)

    def test_oversized_notes_rejected(self):
        data = packet()
        data["decisions"][0]["notes"] = "x" * 2001
        with self.assertRaises(ValueError):
            mod.validate_decisions(data, GROUPS)

if __name__ == "__main__":
    unittest.main()
