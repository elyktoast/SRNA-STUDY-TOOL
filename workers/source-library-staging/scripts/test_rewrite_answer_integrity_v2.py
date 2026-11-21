"""Offline regression tests: AI rewrite must not alter keyed clinical answers."""
import sys
import unittest
from copy import deepcopy
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from item_rewrite_once_v2 import attempt_once


class RewriteAnswerIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.item = {
            "item_id": "saved-intubation-regression", "rules_version": "2.0",
            "mode": "NCE", "domain": "I", "section": "A",
            "objective": "I.A.1", "format": "MC", "model": "test-model",
            "status": "draft", "key": ["C"],
            "options": [
                {"id": "A", "text": "Option A"},
                {"id": "B", "text": "Option B"},
                {"id": "C", "text": "Suspected cribriform plate fracture"},
                {"id": "D", "text": "Option D"},
            ],
            "concept_card": {"evidence_ids": ["passage-page-49"]},
        }
        self.issues = [{"rule_id": "R-2.4", "message": "Source silence"}]

    def test_reject_changed_key(self):
        candidate = {**self.item, "key": ["B"]}
        result = attempt_once(self.item, self.issues, lambda _: candidate, lambda _: [])
        self.assertEqual(result["item"], self.item)
        self.assertEqual(result["rewrite_attempts"], 1)
        self.assertEqual(result["issues"][0]["rule_id"], "R-5.1")
        self.assertFalse(result["can_publish"])

    def test_reject_changed_keyed_text(self):
        candidate = {**self.item, "options": [
            {**o, "text": "Changed answer"} if o["id"] == "C" else o
            for o in self.item["options"]]}
        result = attempt_once(self.item, self.issues, lambda _: candidate, lambda _: [])
        self.assertEqual(result["item"], self.item)
        self.assertEqual(result["issues"][0]["rule_id"], "R-5.1")

    def test_allow_explanation_only_repair(self):
        candidate = {**self.item, "rationale": {"why_key_wins": "Evidence-linked explanation"}}
        result = attempt_once(self.item, self.issues, lambda _: candidate, lambda _: [])
        self.assertEqual(result["item"], candidate)
        self.assertEqual(result["issues"], [])
        self.assertFalse(result["can_publish"])

    def test_provider_outage_consumes_attempt(self):
        def outage(_):
            raise RuntimeError("provider unavailable")
        result = attempt_once(self.item, self.issues, outage, lambda _: [])
        self.assertEqual(result["rewrite_attempts"], 1)
        self.assertTrue(result["rewrite_failed"])
        self.assertEqual(result["item"], self.item)

    def test_no_rewrite_when_no_issues(self):
        result = attempt_once(self.item, [], lambda _: self.fail("called"), lambda _: [])
        self.assertEqual(result["rewrite_attempts"], 0)

    def test_flagged_concept_can_append_newly_retrieved_trusted_sources(self):
        candidate = deepcopy(self.item)
        original_id = self.item["concept_card"]["evidence_ids"][0]
        trusted = [{"passage_id":original_id}]
        candidate["concept_card"]["evidence_ids"].append("new-positive-definition")
        candidate["evidence"] = [{"passage_id":original_id}, {"passage_id":"new-positive-definition"}]
        def rewrite(request):
            self.assertTrue(request["allow_concept_evidence_additions"])
            trusted.append({"passage_id":"new-positive-definition"})
            return candidate
        result = attempt_once(self.item,[{"rule_id":"R-2.4","field":"concept_card.counterfactual"}],
                              rewrite,lambda _:[],trusted_passages=trusted)
        self.assertEqual(result["issues"],[])
        self.assertEqual(result["item"],candidate)
        self.assertEqual(result["rewrite_attempts"],1)
        self.assertFalse(result["can_publish"])

    def test_source_repair_cannot_drop_reorder_forge_or_omit_citations(self):
        original_id = self.item["concept_card"]["evidence_ids"][0]
        trusted = [{"passage_id":original_id},{"passage_id":"new-positive-definition"}]
        issues = [{"rule_id":"R-2.4","field":"concept_card.counterfactual"}]
        for change in ("drop", "reorder", "foreign", "uncited", "duplicate", "malformed"):
            candidate = deepcopy(self.item)
            candidate["concept_card"]["evidence_ids"] = [original_id,"new-positive-definition"]
            candidate["evidence"] = [{"passage_id":pid} for pid in candidate["concept_card"]["evidence_ids"]]
            if change=="drop": candidate["concept_card"]["evidence_ids"]=["new-positive-definition"]
            if change=="reorder": candidate["concept_card"]["evidence_ids"].reverse()
            if change=="foreign": candidate["concept_card"]["evidence_ids"].append("foreign")
            if change=="uncited": candidate["evidence"]=[{"passage_id":original_id}]
            if change=="duplicate": candidate["concept_card"]["evidence_ids"].append(original_id)
            if change=="malformed": candidate["evidence"]=None
            with self.subTest(change=change):
                result=attempt_once(self.item,issues,lambda _:candidate,lambda _:[],trusted_passages=trusted)
                self.assertEqual(result["item"],self.item)
                self.assertIn("R-2.5",[i["rule_id"] for i in result["issues"]])

    def test_unrelated_repair_cannot_expand_concept_sources(self):
        candidate=deepcopy(self.item)
        candidate["concept_card"]["evidence_ids"].append("new-positive-definition")
        candidate["evidence"]=[{"passage_id":pid} for pid in candidate["concept_card"]["evidence_ids"]]
        result=attempt_once(self.item,[{"rule_id":"R-4.2"}],lambda _:candidate,lambda _:[],
                            trusted_passages=candidate["evidence"])
        self.assertEqual(result["item"],self.item)
        self.assertIn("R-2.5",[i["rule_id"] for i in result["issues"]])


if __name__ == "__main__":
    unittest.main()
