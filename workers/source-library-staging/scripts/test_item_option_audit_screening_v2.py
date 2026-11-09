import unittest
from item_option_audit_screening_v2 import attach


class OptionAuditScreeningTests(unittest.TestCase):
    def test_matches_are_not_clinical_verification(self):
        result = {"screening": {"stages": {"evidence": {"status": "pass"}},
                                "screening_complete": True, "can_publish": True},
                  "can_publish": True}
        out = attach(result, {"all_options_searched": True,
                              "all_options_have_matches": True})
        self.assertEqual(out["screening"]["stages"]["independent_option_evidence"]["status"], "pending")
        self.assertFalse(out["screening"]["screening_complete"])
        self.assertFalse(out["can_publish"])

    def test_failed_search_remains_pending(self):
        result = {"screening": {"stages": {}}}
        out = attach(result, {"all_options_searched": False})
        self.assertIn("failed", out["screening"]["stages"]["independent_option_evidence"]["reason"])
        self.assertEqual(out["screening"]["pending_verifications"], ["independent_option_evidence"])


if __name__ == "__main__":
    unittest.main()
