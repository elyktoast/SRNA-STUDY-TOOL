import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_standard_v2 import check
from item_validation_pipeline import screen

def sample():
    return dict(item_id="new-1", rules_version="2.0", model="test", mode="NCE",
        domain="III", section="H", objective="III.H.4", format="MC",
        reasoning_level="application", population="adult", crisis_scenario=False,
        concept_card=dict(objective="III.H.4", mechanism="m", relevance="r",
                          misconception="x", counterfactual="c", evidence_ids=["p1"]),
        stem="Which option is appropriate?",
        select_count=None,
        options=[dict(id=k, text=v, error_pattern=None if k == "A" else "wrong timing")
                 for k,v in zip("ABCD", ("Option alpha", "Option beta", "Option gamma", "Option delta"))],
        sa=None, dd=None, hs=None, key=["A"],
        rationale=dict(core_concept="c", why_key_wins="w", trap="t", distractor_breakdown={"B":"b"}),
        evidence=[dict(textbook_id="t1", passage_id="p1", pdf_page=1)],
        distractor_evidence={"B":"p1"}, numbers_verified_against_page_image=False,
        enemy_ids=[], self_check=dict(rules_checked=[], failed_then_fixed=[], blind_solve="pending"),
        status="draft", audit=[], stats=dict(n_responses=0, p_value=None, point_biserial=None, distractor_pct={}))

class StandardTests(unittest.TestCase):
    def test_valid_structural_item_is_not_approved(self):
        item = sample()
        self.assertEqual(check(item), [])
        result = screen(item)
        self.assertFalse(result["can_publish"])
        self.assertEqual(result["stages"]["blind_model"]["status"], "pending")
        self.assertEqual(result["stages"]["human_review"]["status"], "pending")

    def test_rejects_old_multi_format(self):
        item = sample()
        item.update(format="MS", options=item["options"] + [
            dict(id=k, text=k, error_pattern="wrong timing") for k in "EF"],
            key=["A", "B"], select_count=2, stem="Which are correct? (Select 2.)")
        self.assertEqual(check(item), [])
        item["options"].extend([dict(id="G", text="G", error_pattern="wrong timing")])
        self.assertTrue(any(e["rule_id"] == "R-7.2.2" for e in check(item)))

    def test_flags_long_key_and_correctness_labels(self):
        item = sample()
        item["options"][0]["text"] = "Ensure the patient is awake and all rescue equipment is available immediately"
        item["options"][0]["error_pattern"] = "Correct"
        item["options"][1]["error_pattern"] = "Incorrect: not advised"
        rules = {issue["rule_id"] for issue in check(item)}
        self.assertNotIn("R-6.8", rules)  # Length imbalance is an editorial flag, not a schema failure
        self.assertIn("R-6.3", rules)

    def test_malformed_option_text_returns_diagnostics_not_exception(self):
        for bad in (None, 17, [], {"unexpected": True}):
            with self.subTest(bad=repr(bad)):
                item = sample()
                item["options"][0]["text"] = bad
                rules = {issue["rule_id"] for issue in check(item)}
                self.assertIn("R-15", rules)

    def test_non_object_option_returns_diagnostics_not_exception(self):
        item = sample()
        item["options"][1] = None
        rules = {issue["rule_id"] for issue in check(item)}
        self.assertIn("R-15", rules)

    def test_banned_format_and_missing_evidence(self):
        item = sample()
        item["format"] = "TF"
        item["evidence"] = []
        rules = {e["rule_id"] for e in check(item)}
        self.assertIn("R-7.6", rules)
        self.assertIn("R-2.5", rules)
        self.assertEqual(screen(item)["next_state"], "needs_source_review")

if __name__ == "__main__":
    unittest.main()
