import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nbcrna_classifier import suggest, classify_passages
from nbcrna_coverage import report

class ClassifierTests(unittest.TestCase):
    def test_specific_match(self):
        result = suggest("The variable bypass vaporizer uses fresh gas flow.")
        self.assertEqual(result["status"], "suggested")
        self.assertEqual(result["candidates"][0]["section"], "A")
        self.assertTrue(result["requires_review"])

    def test_ambiguous(self):
        result = suggest("Succinylcholine and capnography waveform are discussed.")
        self.assertEqual(result["status"], "ambiguous")

    def test_abstains_on_unmatched_text(self):
        self.assertEqual(suggest("An unrelated paragraph.")["status"], "unclassified")
        self.assertEqual(classify_passages([{"passage_id": "p1", "excerpt": ""}])[0]["status"], "unclassified")

    def test_coverage_shortfall(self):
        result = report([], [{"passage_id": "p1", "excerpt": "soda lime"}], mode="SEE")
        self.assertEqual(list(result["targets"].values()), [25, 25, 25, 25])
        self.assertEqual(sum(result["question_shortfalls"].values()), 100)
        self.assertFalse(result["passage_classifications_are_verified"])

if __name__ == "__main__":
    unittest.main()
