import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_blind_attestation_v2 import sign
from item_verified_blind_handoff_v2 import attach_verified

SECRET = b"test-only-signing-secret-of-at-least-32-bytes"
def report():
    return {"stages": {k: {"status": "pass", "issues": []} for k in
            ("schema", "deterministic_text", "math", "evidence", "duplicates", "blind_model", "human_review")},
            "can_publish": False}
def envelope():
    return sign(item_id="new-1", run_id="run-1", secret=SECRET,
                result={"status": "pass", "issues": [], "generator_model_id": "a",
                        "reviewer_model_id": "b", "human_review_required": True,
                        "can_publish": False})
class VerifiedHandoffTests(unittest.TestCase):
    def test_signed_review_can_be_attached(self):
        result = attach_verified(report(), envelope(), item_id="new-1", run_id="run-1", secret=SECRET)
        self.assertEqual(result["stages"]["blind_model"]["status"], "pass")
        self.assertFalse(result["can_publish"])
    def test_tampering_rejected(self):
        altered = copy.deepcopy(envelope())
        altered["result"]["status"] = "flag"
        with self.assertRaises(ValueError):
            attach_verified(report(), altered, item_id="new-1", run_id="run-1", secret=SECRET)
    def test_wrong_run_rejected(self):
        with self.assertRaises(ValueError):
            attach_verified(report(), envelope(), item_id="new-1", run_id="run-2", secret=SECRET)
    def test_wrong_item_rejected(self):
        with self.assertRaises(ValueError):
            attach_verified(report(), envelope(), item_id="other", run_id="run-1", secret=SECRET)
    def test_wrong_secret_rejected(self):
        with self.assertRaises(ValueError):
            attach_verified(report(), envelope(), item_id="new-1", run_id="run-1",
                            secret=b"some-other-signing-key-at-least-32-bytes")

if __name__ == "__main__":
    unittest.main()
