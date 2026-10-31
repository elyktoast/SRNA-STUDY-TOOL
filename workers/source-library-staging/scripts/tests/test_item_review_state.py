import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_review_state import transition

def report(blind="pending", human="pending"):
    names = ("schema", "deterministic_text", "math", "evidence", "duplicates")
    return {"stages": {**{k: {"status": "pass"} for k in names},
                       "blind_model": {"status": blind}, "human_review": {"status": human}}}

class ReviewStateTests(unittest.TestCase):
    def test_draft_cannot_publish(self):
        with self.assertRaises(ValueError):
            transition({"status": "draft"}, "published", actor_id="r1",
                       actor_roles=("publisher",), checks=report("pass", "pass"))
    def test_source_reviewer_required(self):
        with self.assertRaises(PermissionError):
            transition({"status": "needs_source_review"}, "verified_evidence",
                       actor_id="r1", checks=report())
    def test_verified_requires_checks(self):
        with self.assertRaises(ValueError):
            transition({"status": "needs_source_review"}, "verified_evidence",
                       actor_id="r1", actor_roles=("source_reviewer",),
                       checks={"stages": {"schema": {"status": "pass"}}})
    def test_human_approval_required(self):
        with self.assertRaises(ValueError):
            transition({"status": "verified_evidence"}, "approved",
                       actor_id="r2", actor_roles=("clinical_reviewer",),
                       checks=report("pass", "pending"))
    def test_authorized_review_is_audited_and_immutable(self):
        item = {"status": "verified_evidence", "audit": []}
        result = transition(item, "approved", actor_id="faculty-1",
                            actor_roles=("clinical_reviewer",),
                            checks=report("pass", "pass"))
        self.assertEqual(result["status"], "approved")
        self.assertEqual(item["status"], "verified_evidence")
        self.assertEqual(len(result["audit"]), 1)
        self.assertEqual(result["audit"][0]["who"], "faculty-1")
    def test_retired_cannot_republish(self):
        with self.assertRaises(ValueError):
            transition({"status": "retired"}, "published", actor_id="r1",
                       actor_roles=("publisher",), checks=report("pass", "pass"))

if __name__ == "__main__":
    unittest.main()
