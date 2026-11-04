import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_rewrite_once_v2 import attempt_once


def draft():
    return {"item_id": "q1", "rules_version": "2.0", "mode": "NCE",
            "domain": "III", "section": "H", "objective": "III.H.4",
            "format": "MC", "model": "trusted-model", "status": "draft",
            "stem": "Original"}


class RewriteTests(unittest.TestCase):
    def test_no_issues_no_rewrite(self):
        def forbidden(_):
            self.fail("Rewrite must not run")
        result = attempt_once(draft(), [], forbidden, lambda item: [])
        self.assertEqual(result["rewrite_attempts"], 0)
        self.assertFalse(result["can_publish"])

    def test_single_rewrite_and_revalidation(self):
        calls = []
        def rewrite(request):
            calls.append(request)
            result = request["item"]
            result["stem"] = "Revised"
            return result
        result = attempt_once(draft(), [{"rule_id": "R-4.1"}], rewrite,
                              lambda item: [] if item["stem"] == "Revised" else [{"rule_id": "R-4.1"}])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["rewrite_attempts"], 1)
        self.assertEqual(result["issues"], [])
        self.assertFalse(result["can_publish"])

    def test_rejects_model_metadata_and_approval_changes(self):
        for field, value in (("model", "forged"), ("item_id", "forged"),
                             ("status", "approved"), ("objective", "I.A.1")):
            with self.subTest(field=field):
                def rewrite(request):
                    item = request["item"]
                    item[field] = value
                    return item
                result = attempt_once(draft(), [{"rule_id": "R-15"}], rewrite,
                                      lambda item: self.fail("Must not validate forged rewrite"))
                self.assertEqual(result["item"], draft())
                self.assertEqual(result["rewrite_attempts"], 1)
                self.assertFalse(result["can_publish"])


if __name__ == "__main__":
    unittest.main()
