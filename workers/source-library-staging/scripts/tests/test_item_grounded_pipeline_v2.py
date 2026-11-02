import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_grounded_pipeline_v2 import generate_from_index

KW = dict(mode="NCE", domain="III", section="III.H", objective="III.H.4",
          item_id="draft-1")
SOURCE = {"passage_id": "p1", "textbook_id": "t1", "excerpt": "Indexed text",
          "pdf_page_start": 10, "pdf_page_end": 11, "citation_verified": False}
PACKET = {"topic": "airway", "can_generate_grounded_questions": True,
          "sources": [SOURCE]}


class IndexedPipelineTests(unittest.TestCase):
    @patch("item_grounded_pipeline_v2.generate_and_screen")
    @patch("item_grounded_pipeline_v2.build_evidence")
    def test_retrieval_to_screening_preserves_review_gate(self, retrieve, screen):
        retrieve.return_value = PACKET
        screen.return_value = {"next_state": "draft", "can_publish": True,
                               "database_writes": True}
        result = generate_from_index(object(), "owner-1", "airway", lambda r: {},
                                     **KW, textbook_id="t1")
        retrieve.assert_called_once()
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
