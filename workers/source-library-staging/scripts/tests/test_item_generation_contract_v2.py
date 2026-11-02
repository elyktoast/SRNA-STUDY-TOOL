import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_contract_v2 import build_step, validate_complete_item
from test_item_standard_v2 import sample

EVIDENCE = [{"passage_id": "p1", "textbook_id": "t1", "excerpt": "Source text"}]
BASE = dict(mode="NCE", domain="III", section="III.H", objective="III.H.4", evidence=EVIDENCE)

class ContractTests(unittest.TestCase):
    def test_concept_then_draft_then_rationale(self):
        concept = build_step("concept_card", **BASE)
        self.assertEqual(concept["required_output"], "concept_card")
        with self.assertRaises(ValueError):
            build_step("item_draft", **BASE, format="MC")
        draft = build_step("item_draft", **BASE, format="MC", concept_card={"objective": "x"})
        self.assertFalse(draft["auto_publish"])
        with self.assertRaises(ValueError):
            build_step("rationale", **BASE, format="MC", concept_card={"objective": "x"})
        rationale = build_step("rationale", **BASE, format="MC", concept_card={"objective": "x"}, draft={"stem": "s"})
        self.assertEqual(rationale["required_output"], "rationale")
    def test_reject_unsupported_format_and_missing_evidence(self):
        with self.assertRaises(ValueError):
            build_step("item_draft", **BASE, format="TF", concept_card={})
        with self.assertRaises(ValueError):
            build_step("concept_card", **dict(BASE, evidence=[]))
    def test_schema_validation(self):
        self.assertEqual(validate_complete_item(sample()), [])
        self.assertTrue(validate_complete_item({"rules_version": "1.0"}))

if __name__ == "__main__":
    unittest.main()
