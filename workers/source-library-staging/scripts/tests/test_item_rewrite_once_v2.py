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

    def test_rewrite_request_targets_reported_evidence_defects(self):
        original = draft()
        issues = [{"rule_id": "R-2.5", "message": "Excerpt mismatch"},
                  {"rule_id": "R-12.4", "message": "Missing option evidence"}]
        captured = []
        def rewrite(request):
            captured.append(request)
            return request["item"]
        result = attempt_once(original, issues, rewrite, lambda item: issues)
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0]["issues"], issues)
        guidance = captured[0]["repair_instructions"]
        for phrase in ("Fix only", "R-2.5", "R-12.4", "verbatim",
                       "source silence", "unpublished", "clinical review"):
            self.assertIn(phrase, guidance)
        self.assertEqual(captured[0]["max_rewrites"], 1)
        self.assertEqual(result["rewrite_attempts"], 1)
        self.assertFalse(result["can_publish"])
        self.assertEqual(original, draft())

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


    def test_rewrite_cannot_claim_page_image_verification(self):
        original = {**draft(), "numbers_verified_against_page_image": False}
        def revise(request):
            item = request["item"]
            item["numbers_verified_against_page_image"] = True
            return item
        result = attempt_once(original, [{"rule_id": "R-6.8"}], revise,
                              lambda item: self.fail("Forged verification must not validate"))
        self.assertEqual(result["item"], original)
        self.assertTrue(any(i["rule_id"] == "R-13" for i in result["issues"]))

    def test_rewrite_provider_failure_preserves_original(self):
        def unavailable(request):
            raise RuntimeError("unavailable")
        issues = [{"rule_id": "R-2.5"}]
        result = attempt_once(draft(), issues, unavailable, lambda item: [])
        self.assertEqual(result["item"], draft())
        self.assertEqual(result["issues"], issues)
        self.assertEqual(result["rewrite_attempts"], 1)
        self.assertTrue(result["rewrite_failed"])

    def test_rewrite_validator_failure_preserves_original(self):
        def revise(request):
            item = request["item"]
            item["stem"] = "Changed"
            return item
        def broken(item):
            raise ValueError("invalid")
        result = attempt_once(draft(), [{"rule_id": "R-15"}], revise, broken)
        self.assertEqual(result["item"], draft())
        self.assertTrue(result["rewrite_failed"])

    def test_rewrite_cannot_replace_concept_evidence(self):
        original = {**draft(), "concept_card": {"evidence_ids": ["passage-1"]}}
        def revise(request):
            item = request["item"]
            item["concept_card"]["evidence_ids"] = ["passage-2"]
            return item
        result = attempt_once(original, [{"rule_id": "R-15"}], revise,
                              lambda item: self.fail("Untrusted evidence must not validate"))
        self.assertEqual(result["item"], original)
        self.assertTrue(any(issue["rule_id"] == "R-2.5" for issue in result["issues"]))


if __name__ == "__main__":
    unittest.main()
