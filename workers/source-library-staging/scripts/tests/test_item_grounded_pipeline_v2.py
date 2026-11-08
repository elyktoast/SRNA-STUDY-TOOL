import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_grounded_pipeline_v2 import generate_from_index

KW = dict(mode="NCE", domain="III", section="H", objective="III.H.4",
          item_id="draft-1")
SOURCE = {"passage_id": "p1", "textbook_id": "t1", "excerpt": "Indexed text",
          "pdf_page_start": 10, "pdf_page_end": 11, "citation_verified": False}
PACKET = {"topic": "airway", "can_generate_grounded_questions": True,
          "sources": [SOURCE]}


class IndexedPipelineTests(unittest.TestCase):
    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_preverified_packet_prevents_second_database_lookup(self, retrieve, screen):
        screen.return_value = {"next_state": "draft", "screening": {}}
        result = generate_from_index(object(), "owner-1", "airway", lambda r: {},
                                     **KW, textbook_id="t1", evidence_packet=PACKET)
        retrieve.assert_not_called()
        self.assertEqual(screen.call_args.kwargs["evidence"], [SOURCE])
        self.assertEqual(result["source_evidence"]["passage_ids"], ["p1"])


    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_chapter_and_page_filters_forwarded(self, retrieve, screen):
        retrieve.return_value = PACKET
        screen.return_value = {"next_state": "draft", "screening": {}}
        generate_from_index(object(), "owner-1", "airway", lambda r: {}, **KW,
                            section_id="section-1", include_subsections=True,
                            page_start=10, page_end=20)
        self.assertEqual(retrieve.call_args.kwargs["section_id"], "section-1")
        self.assertTrue(retrieve.call_args.kwargs["include_subsections"])
        self.assertEqual(retrieve.call_args.kwargs["page_start"], 10)
        self.assertEqual(retrieve.call_args.kwargs["page_end"], 20)

    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_retrieval_to_screening_preserves_review_gate(self, retrieve, screen):
        retrieve.return_value = PACKET
        screen.return_value = {"next_state": "draft", "can_publish": True,
                               "database_writes": True}
        result = generate_from_index(object(), "owner-1", "airway", lambda r: {},
                                     **KW, textbook_id="t1")
        retrieve.assert_called_once()
        self.assertEqual(retrieve.call_args.kwargs["limit"], 8)
        self.assertEqual(screen.call_args.kwargs["evidence"], [SOURCE])
        self.assertEqual(result["source_evidence"]["passage_ids"], ["p1"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])
        self.assertTrue(result["requires_human_review"])

    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_empty_index_blocks_model(self, retrieve, screen):
        retrieve.return_value = {"topic": "airway", "sources": [],
                                 "can_generate_grounded_questions": False}
        with self.assertRaisesRegex(ValueError, "No indexed textbook evidence"):
            generate_from_index(object(), "owner-1", "airway", lambda r: {}, **KW)
        screen.assert_not_called()

    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_all_modes_and_formats_preserve_source_and_review_gate(self, retrieve, screen):
        retrieve.return_value = PACKET
        screen.return_value = {"next_state": "draft", "can_publish": True, "database_writes": True}
        for mode in ("NCE", "SEE"):
            for format_name in ("MC", "MS", "SA", "DD", "HS"):
                with self.subTest(mode=mode, format=format_name):
                    result = generate_from_index(object(), "owner-1", "airway", lambda r: {},
                                                 **dict(KW, mode=mode), format=format_name)
                    self.assertEqual(screen.call_args.kwargs["mode"], mode)
                    self.assertEqual(screen.call_args.kwargs["format"], format_name)
                    self.assertEqual(screen.call_args.kwargs["evidence"], [SOURCE])
                    self.assertFalse(result["can_publish"])
                    self.assertFalse(result["database_writes"])
                    self.assertTrue(result["requires_human_review"])
                    self.assertTrue(result["source_evidence"]["pdf_page_locations_only"])
                    self.assertFalse(result["source_evidence"]["printed_page_citations_verified"])

    @patch("item_generation_screened_v2.intake")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_real_index_to_three_stage_generator_to_screening(self, retrieve, intake):
        from test_item_standard_v2 import sample
        retrieve.return_value = PACKET
        steps = []
        def adapter(request):
            steps.append(request["step"])
            if request["step"] == "concept_card":
                return dict(objective="III.H.4", mechanism="m", relevance="r",
                            misconception="x", counterfactual="y", evidence_ids=["p1"])
            if request["step"] == "item_draft":
                item = sample()
                item["evidence"] = [{"textbook_id": "t1", "passage_id": "p1",
                                    "pdf_page": 10, "excerpt": "Indexed text"}]
                item["distractor_evidence"] = {
                    option["id"]: {
                        "verdict": "supports_key" if option["id"] == "A" else "refutes_distractor",
                        "passage_ids": ["p1"], "explanation": "Indexed source justification"
                    } for option in item["options"]
                }
                return item
            return dict(core_concept="a", why_key_wins="b", trap="c",
                        distractor_breakdown={"B": "wrong"})
        intake.return_value = {"draft_reviews": [{
            "status": "draft", "screening": {"stages": {"human_review": {"status": "pending"}}}
        }]}
        result = generate_from_index(object(), "owner-1", "airway", adapter, **KW)
        self.assertEqual(steps, ["concept_card", "item_draft", "rationale"])
        self.assertEqual(result["generator_issues"], [], result["generator_issues"])
        intake.assert_called_once()
        self.assertEqual(intake.call_args.kwargs["passages"]["p1"]["text"], "Indexed text")
        self.assertEqual(result["item"]["status"], "draft")
        self.assertEqual(result["source_evidence"]["passage_ids"], ["p1"])
        self.assertFalse(result["source_evidence"]["printed_page_citations_verified"])
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])

    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_invalid_indexed_evidence_blocks_all_model_steps(self, retrieve):
        invalid = [
            [{**SOURCE, "citation_verified": True}],
            [{**SOURCE, "excerpt": ""}],
            [{**SOURCE, "pdf_page_start": 0}],
            [{**SOURCE, "pdf_page_end": 9}],
            [{**SOURCE, "pdf_page_start": "10"}],
            [SOURCE, {**SOURCE}],
            [{**SOURCE, "passage_id": None}],
        ]
        for sources in invalid:
            with self.subTest(sources=sources):
                retrieve.return_value = {**PACKET, "sources": sources}
                steps = []
                with self.assertRaisesRegex(ValueError, "Invalid or unverified"):
                    generate_from_index(object(), "owner-1", "airway",
                                        lambda request: steps.append(request), **KW)
                self.assertEqual(steps, [])

    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_review_repair_adapter_forwarded(self, retrieve, screen):
        retrieve.return_value = PACKET
        screen.return_value = {"next_state": "draft"}
        def repair(request):
            return request["item"]
        generate_from_index(object(), "owner-1", "airway", lambda r: {},
                            **KW, review_repair=repair)
        self.assertIs(screen.call_args.kwargs["review_repair"], repair)

    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_invalid_review_repair_blocks_retrieval(self, retrieve):
        with self.assertRaisesRegex(ValueError, "repair adapter"):
            generate_from_index(object(), "owner-1", "airway", lambda r: {},
                                **KW, review_repair="not callable")
        retrieve.assert_not_called()

    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_missing_adapter_blocks_retrieval(self, retrieve):
        with self.assertRaisesRegex(ValueError, "generator adapter"):
            generate_from_index(object(), "owner-1", "airway", None, **KW)
        retrieve.assert_not_called()

    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_same_blind_model_blocks_retrieval(self, retrieve):
        with self.assertRaisesRegex(ValueError, "distinct model identities"):
            generate_from_index(object(), "owner-1", "airway", lambda r: {}, **KW,
                                blind_reviewer=lambda r: {},
                                generator_model_id="same", reviewer_model_id="same")
        retrieve.assert_not_called()


if __name__ == "__main__":
    unittest.main()
