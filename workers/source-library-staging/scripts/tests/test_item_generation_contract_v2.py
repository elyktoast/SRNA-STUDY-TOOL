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
    def test_all_ten_exam_mode_format_combinations_preserve_review_gates(self):
        for mode in ("NCE", "SEE"):
            for format_name in ("MC", "MS", "SA", "DD", "HS"):
                with self.subTest(mode=mode, format=format_name):
                    base = dict(BASE, mode=mode)
                    concept = build_step("concept_card", **base)
                    draft = build_step("item_draft", **base, format=format_name,
                                       concept_card={"objective": "III.H.4"})
                    rationale = build_step("rationale", **base, format=format_name,
                                           concept_card={"objective": "III.H.4"},
                                           draft={"stem": "Question"})
                    self.assertEqual([concept["step"], draft["step"], rationale["step"]],
                                     ["concept_card", "item_draft", "rationale"])
                    for request in (concept, draft, rationale):
                        self.assertTrue(request["human_review_required"])
                        self.assertFalse(request["auto_publish"])
                        self.assertEqual(request["mode"], mode)
                    self.assertEqual(draft["format"], format_name)
                    self.assertEqual(rationale["format"], format_name)

    def test_schema_validation(self):
        self.assertEqual(validate_complete_item(sample()), [])
        self.assertTrue(validate_complete_item({"rules_version": "1.0"}))

if __name__ == "__main__":
    unittest.main()
