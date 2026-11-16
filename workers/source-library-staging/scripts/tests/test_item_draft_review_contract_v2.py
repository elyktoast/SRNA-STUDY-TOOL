import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_draft_review_contract_v2 import validate_draft, validate_review

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "2a589498-aaa4-410f-b51a-00d3ab99eafd"

class DraftReviewTests(unittest.TestCase):
    def test_automated_quality_flags_require_revision_without_approving_content(self):
        for status in ('flag', 'fail'):
            with self.subTest(status=status):
                data = dict(owner_uid=OWNER, textbook_id=BOOK, mode='NCE', format='MC',
                            question={'stem': 'Preserve this draft'},
                            screening={'stages': {'explanation_evidence': {'status': status}}},
                            evidence=[{'passage_id': 'passage', 'textbook_id': BOOK}])
                original = repr(data)
                outcome = validate_draft(data)
                self.assertEqual(outcome['status'], 'needs_revision')
                self.assertTrue(outcome['requires_human_review'])
                self.assertFalse(outcome['published'])
                self.assertEqual(repr(data), original)

    def test_pending_duplicate_or_human_checks_do_not_claim_automated_failure(self):
        data = dict(owner_uid=OWNER, textbook_id=BOOK, mode='NCE', format='MC',
                    question={}, screening={'stages': {
                        'schema': {'status': 'pass'},
                        'duplicates': {'status': 'pending'},
                        'human_review': {'status': 'pending'}}},
                    evidence=[{'passage_id': 'passage', 'textbook_id': BOOK}])
        self.assertEqual(validate_draft(data)['status'], 'pending_review')

    def test_valid_draft_requires_human_review(self):
        data = dict(owner_uid=OWNER, textbook_id=BOOK, mode="NCE", format="MC",
                    question={"stem": "Example"}, screening={},
                    evidence=[{"passage_id": "passage", "textbook_id": BOOK}])
        result = validate_draft(data)
        self.assertTrue(result["requires_human_review"])
        self.assertFalse(result["published"])

    def test_rejects_wrong_textbook_evidence(self):
        data = dict(owner_uid=OWNER, textbook_id=BOOK, mode="NCE", format="MC",
                    question={}, screening={},
                    evidence=[{"passage_id": "passage", "textbook_id": OWNER}])
        with self.assertRaises(ValueError):
            validate_draft(data)

    def test_approval_requires_notes_and_identity(self):
        with self.assertRaises(ValueError):
            validate_review("approved_for_bank", OWNER, "")
        self.assertFalse(validate_review("approved_for_bank", OWNER, "Checked source")["published"])

if __name__ == "__main__":
    unittest.main()
