import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_generation_runner_v2 import generate_one, _repair_ellipsized_citations, _hydrate_indexed_citations, _complete_nonclinical_schema_fields
from test_item_standard_v2 import sample

EVIDENCE = [{"passage_id": "p1", "textbook_id": "t1", "excerpt": "Source"}]
ARGS = dict(mode="NCE", domain="III", section="III.H", objective="III.H.4",
            evidence=EVIDENCE, format="MC", item_id="new-1")

class RunnerTests(unittest.TestCase):
    def test_three_separate_calls_and_never_approve(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            self.assertEqual(request["format"], "MC")
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                return dict(sample())
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        result = generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        self.assertEqual(result["item"]["status"], "draft")
        self.assertFalse(result["auto_approved"])
        self.assertFalse(result["database_writes"])
    def test_trusted_model_overrides_untrusted_model_before_validation(self):
        def adapter(request):
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                draft = sample()
                draft["model"] = "forged-model"
                return draft
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        result = generate_one(adapter, **ARGS, generator_model_id="trusted-model")
        self.assertEqual(result["item"]["model"], "trusted-model")
        self.assertFalse(result["auto_approved"])

    def test_unknown_evidence_stops_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="o", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids=["unknown"])
        with self.assertRaises(ValueError):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])
    def test_duplicate_concept_citations_stop_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="III.H.4", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids=["p1", "p1"])
        with self.assertRaisesRegex(ValueError, "unique passage IDs"):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])

    def test_invalid_concept_citation_type_stops_before_draft(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            return dict(objective="III.H.4", mechanism="m", relevance="r",
                        misconception="x", counterfactual="y", evidence_ids="p1")
        with self.assertRaises(ValueError):
            generate_one(adapter, **ARGS)
        self.assertEqual(calls, ["concept_card"])

    def test_untrusted_draft_cannot_override_review_or_identity(self):
        calls = []
        def adapter(request):
            calls.append(request["step"])
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                draft = sample()
                draft.update(item_id="model-forged-id", mode="SEE", domain="I",
                             section="forged", objective="forged", format="MC",
                             status="approved", rules_version="1.0")
                return draft
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        result = generate_one(adapter, **ARGS)
        item = result["item"]
        for field, expected in (("item_id", "new-1"), ("mode", "NCE"),
                                ("domain", "III"), ("section", "III.H"),
                                ("objective", "III.H.4"), ("status", "draft"),
                                ("rules_version", "2.0")):
            with self.subTest(field=field):
                self.assertEqual(item[field], expected)
        self.assertEqual(calls, ["concept_card", "item_draft", "rationale"])
        self.assertFalse(result["auto_approved"])
        self.assertFalse(result["database_writes"])

    def test_malformed_adapter_response_stops_pipeline(self):
        for invalid in (None, [], "not-json"):
            with self.subTest(response=repr(invalid)):
                calls = []
                def adapter(request):
                    calls.append(request["step"])
                    return invalid
                with self.assertRaisesRegex(ValueError, "JSON object"):
                    generate_one(adapter, **ARGS)
                self.assertEqual(calls, ["concept_card"])

    def test_repairs_only_unique_ordered_verbatim_ellipsis(self):
        passage = "Jaw wiring requires extreme caution before extubating. The airway must be thoroughly suctioned, the throat pack removed, the patient wide awake, and equipment on hand to quickly cut the wires."
        sources = [{"passage_id": "p1", "textbook_id": "t1", "excerpt": passage}]
        draft = {"evidence": [{"passage_id": "p1", "textbook_id": "t1",
                               "excerpt": "Jaw wiring requires extreme caution before extubating. ... equipment on hand to quickly cut the wires."}]}
        result = _repair_ellipsized_citations(draft, sources)
        self.assertEqual(result["evidence"][0]["excerpt"], passage)
        self.assertIn("...", draft["evidence"][0]["excerpt"])
        from item_source_reconciliation_v2 import reconcile
        self.assertEqual(reconcile(result, sources), [])

    def test_refuses_unverified_ambiguous_or_wrong_source_quotes(self):
        passage = "First fragment is repeated. First fragment is repeated. Last fragment is unique."
        sources = [{"passage_id": "p1", "textbook_id": "t1", "excerpt": passage}]
        for quote, textbook in [
            ("First fragment is repeated. ... Last fragment is unique.", "t1"),
            ("Invented fragment here ... Last fragment is unique.", "t1"),
            ("Last fragment is unique. ... First fragment is repeated.", "t1"),
            ("First fragment is repeated. ... Last fragment is unique.", "wrong"),
        ]:
            with self.subTest(quote=quote, textbook=textbook):
                draft = {"evidence": [{"passage_id": "p1", "textbook_id": textbook, "excerpt": quote}]}
                self.assertEqual(_repair_ellipsized_citations(draft, sources), draft)

    def test_text_only_generation_never_claims_page_image_verification(self):
        for draft in ({}, {"numbers_verified_against_page_image": True},
                      {"numbers_verified_against_page_image": None}):
            with self.subTest(draft=draft):
                result = _complete_nonclinical_schema_fields(draft)
                self.assertIs(result["numbers_verified_against_page_image"], False)
                self.assertNotEqual(draft, result)

    def test_citation_cannot_claim_page_image_verification(self):
        source = {"passage_id": "p1", "textbook_id": "t1",
                  "pdf_page_start": 7, "excerpt": "Exact indexed text"}
        draft = {"evidence": [{"passage_id": "p1", "textbook_id": "t1",
                              "pdf_page": 7, "numbers_verified_against_page_image": True}]}
        result = _hydrate_indexed_citations(draft, [source])
        self.assertNotIn("numbers_verified_against_page_image", result["evidence"][0])
        self.assertEqual(result["evidence"][0]["excerpt"], source["excerpt"])
        self.assertTrue(draft["evidence"][0]["numbers_verified_against_page_image"])

    def test_no_implicit_model_calls(self):
        with self.assertRaises(ValueError):
            generate_one(None, **ARGS)

    def test_missing_quote_materializes_only_from_bound_indexed_source(self):
        source = {"passage_id": "p1", "textbook_id": "t1", "pdf_page_start": 7,
                  "excerpt": "Exact hyphen-\nated indexed text with a ﬁ ligature."}
        draft = {"evidence": [{"passage_id": "p1", "textbook_id": "t1", "pdf_page": 7}]}
        hydrated = _hydrate_indexed_citations(draft, [source])
        self.assertEqual(hydrated["evidence"][0]["excerpt"], source["excerpt"])
        self.assertNotIn("excerpt", draft["evidence"][0])

    def test_hydration_never_overwrites_fabricated_quotes_or_wrong_references(self):
        source = {"passage_id": "p1", "textbook_id": "t1", "pdf_page_start": 7, "excerpt": "Trusted source"}
        for citation in [
            {"passage_id": "p1", "textbook_id": "wrong", "pdf_page": 7},
            {"passage_id": "unknown", "textbook_id": "t1", "pdf_page": 7},
            {"passage_id": "p1", "textbook_id": "t1", "pdf_page": 8},
            {"passage_id": "p1", "textbook_id": "t1", "pdf_page": 7, "excerpt": "Invented quotation"},
            {"passage_id": "p1", "textbook_id": "t1", "pdf_page": 7, "excerpt": ""},
            "", "invalid citation",
        ]:
            with self.subTest(citation=citation):
                draft = {"evidence": [citation]}
                self.assertEqual(_hydrate_indexed_citations(draft, [source]), draft)

    def test_known_option_references_receive_citations_but_unknown_references_do_not(self):
        source = {"passage_id":"p1","textbook_id":"t1","pdf_page_start":7,"excerpt":"Trusted source"}
        draft = {"evidence":[],"distractor_evidence":{"A":{"passage_ids":["p1","unknown"]}}}
        result = _hydrate_indexed_citations(draft,[source])
        self.assertEqual(result["evidence"],[{"passage_id":"p1","textbook_id":"t1","pdf_page":7,"excerpt":"Trusted source", "printed_page_verified":False,"edition":None,"chapter":None,"edition_status":"not_recorded"}])
        self.assertIn("unknown",result["distractor_evidence"]["A"]["passage_ids"])
        self.assertEqual(draft["evidence"],[])

if __name__ == "__main__":
    unittest.main()
