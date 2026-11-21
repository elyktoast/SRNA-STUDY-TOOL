import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from build_question_evidence import build_evidence

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"


class EvidenceTests(unittest.TestCase):
    def test_evidence_retains_provenance_and_disclaims_printed_pages(self):
        row = {"passage_id": "passage-1", "textbook_id": "book-1",
               "filename": "book.pdf", "pdf_page_start": 10, "pdf_page_end": 11,
               "excerpt": "Supported text"}
        with patch("build_question_evidence.search", return_value=[row]) as mock:
            result = build_evidence(object(), OWNER, "airway", limit=3)
        self.assertTrue(result["can_generate_grounded_questions"])
        self.assertFalse(result["sources"][0]["citation_verified"])
        self.assertEqual(result["sources"][0]["passage_id"], "passage-1")
        self.assertEqual(result["sources"][0]["citation_type"], "physical_pdf_page_1_based")
        mock.assert_called_once()

    def test_no_evidence_blocks_grounded_generation(self):
        with patch("build_question_evidence.search", return_value=[]):
            result = build_evidence(object(), OWNER, "uncovered topic")
        self.assertFalse(result["can_generate_grounded_questions"])
        self.assertEqual(result["sources"], [])

    def test_rejects_blank_and_oversized_topics(self):
        for topic in (" ", "a" * 501):
            with self.assertRaises(ValueError):
                build_evidence(object(), OWNER, topic)

    def test_learning_objective_search_omits_only_teaching_prefix_and_preserves_scope(self):
        topic='Explain the relationship between functional residual capacity and oxygen reserve during apnea.'
        query='functional residual capacity and oxygen reserve during apnea.'
        book='8343459f-0595-4375-8ac6-7700e6792abe'
        section='8343459f-0595-4375-8ac6-7700e6792abf'
        conn=object()
        with patch('build_question_evidence.search',return_value=[]) as search:
            result=build_evidence(conn,OWNER,topic,textbook_id=book,section_id=section,
                                  include_subsections=True,page_start=10,page_end=20,limit=3)
        search.assert_called_once_with(conn,query,OWNER,limit=3,textbook_id=book,section_id=section,
                                       include_subsections=True,page_start=10,page_end=20)
        self.assertEqual(result['topic'],topic)
        self.assertFalse(result['can_generate_grounded_questions'])

    def test_topic_terms_and_relations_are_not_silently_broadened(self):
        for topic in ('functional residual capacity and oxygen reserve during apnea',
                      'respiratory physiology','unrecognized concept xyz'):
            with patch('build_question_evidence.search',return_value=[]) as search:
                build_evidence(object(),OWNER,topic)
            self.assertEqual(search.call_args.args[1],topic)


if __name__ == "__main__":
    unittest.main()
