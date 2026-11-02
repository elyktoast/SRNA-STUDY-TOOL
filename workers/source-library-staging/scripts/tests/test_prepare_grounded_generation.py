import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare_grounded_generation import prepare

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"


class PrepareTests(unittest.TestCase):
    def test_generator_contract_contains_source_identifiers(self):
        evidence = {"can_generate_grounded_questions": True, "sources": [
            {"passage_id": "p1", "textbook_id": "t1", "pdf_page_start": 9,
             "pdf_page_end": 10, "excerpt": "Anesthesia source text."}]}
        with patch("prepare_grounded_generation.build_evidence", return_value=evidence):
            result = prepare(object(), OWNER, "anesthesia", count=5)
        self.assertEqual(result["count"], 5)
        self.assertIn("passage_id=p1", result["material"])
        self.assertIn("PDF pages 9-10", result["material"])
        self.assertFalse(result["evidence"]["citation_verified"])
        self.assertTrue(result["evidence"]["requires_human_review"])

    def test_no_evidence_blocks_generation(self):
        with patch("prepare_grounded_generation.build_evidence", return_value={
            "can_generate_grounded_questions": False, "sources": []}):
            with self.assertRaisesRegex(ValueError, "generation blocked"):
                prepare(object(), OWNER, "uncovered")

    def test_invalid_count_rejected(self):
        for count in (0, 21, True):
            with self.assertRaises(ValueError):
                prepare(object(), OWNER, "airway", count=count)


if __name__ == "__main__":
    unittest.main()
