import sys
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_draft_review_contract_v2 import validate_draft, validate_review, approval_issues

OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "2a589498-aaa4-410f-b51a-00d3ab99eafd"

def passed_screening():
    names = ("schema", "deterministic_text", "math", "evidence", "duplicates", "blind_model",
             "explanation_evidence", "editorial_quality", "options_only", "independent_option_evidence")
    stages = {**{name:{"status":"pass", "issues":[]} for name in names},
                       "duplicates":{"status":"pass","issues":[],"search_complete":True,
                                     "index_id":"question_semantic_index_v2:@cf/baai/bge-m3:"+'a'*64},
                       "human_review":{"status":"pending", "issues":[]}}
    return {'stages':stages}

class DraftReviewTests(unittest.TestCase):
    def test_exact_only_or_stale_semantic_reports_cannot_authorize_approval(self):
        screening=passed_screening()
        screening['stages']['duplicates']={'status':'pass','issues':[]}
        self.assertTrue(approval_issues(screening,'MC'))
        with patch.dict('os.environ',{'AI_SEMANTIC_EMBEDDING_OPT_IN':'true','SEMANTIC_INDEX_INVENTORY_PATH':'trusted-path'}), patch('item_semantic_inventory_reconcile_v2.load_inventory',return_value=({},'b'*64)):
            self.assertTrue(any('bank changed' in issue['message'] for issue in approval_issues(passed_screening(),'MC')))
            screening=passed_screening()
            screening['stages']['duplicates']['index_id']='question_semantic_index_v2:@cf/baai/bge-m3:'+'b'*64
            self.assertEqual(approval_issues(screening,'MC'),[])
    def test_approval_requires_all_saved_automated_checks_but_allows_pending_human_review(self):
        self.assertEqual(approval_issues(passed_screening(), "MC"), [])
        for name in passed_screening()["stages"]:
            if name == "human_review":
                continue
            for status in ("flag", "fail", "pending", "unknown", None):
                screening = passed_screening()
                screening["stages"][name]["status"] = status
                self.assertTrue(approval_issues(screening, "MC"), (name,status))
            screening = passed_screening()
            del screening["stages"][name]
            self.assertTrue(approval_issues(screening, "MC"), name)

    def test_malformed_and_contradictory_reports_never_authorize_approval(self):
        for value in (None, {}, {"stages":[]}, {"stages":None}):
            self.assertTrue(approval_issues(value, "MC"))
        screening = passed_screening()
        screening["stages"]["evidence"]["issues"] = [{"rule_id":"R-2.4"}]
        self.assertTrue(approval_issues(screening, "MC"))
        screening = passed_screening()
        screening["stages"]["new_verification"] = {"status":"pending"}
        self.assertTrue(approval_issues(screening, "MC"))

    def test_numeric_and_hotspot_require_trusted_format_verification(self):
        for fmt,name in (("SA","page_image_verification"),("HS","figure_verification")):
            screening = passed_screening()
            self.assertTrue(approval_issues(screening, fmt))
            screening["stages"][name] = {"status":"pass", "issues":[]}
            self.assertEqual(approval_issues(screening, fmt), [])
    def test_automated_quality_flags_require_revision_without_approving_content(self):
        for status in ('flag', 'fail', 'pending'):
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

    def test_pending_automated_checks_are_held_but_pending_human_review_is_allowed(self):
        data = dict(owner_uid=OWNER, textbook_id=BOOK, mode='NCE', format='MC',
                    question={}, screening={'stages': {
                        'schema': {'status': 'pass'},
                        'duplicates': {'status': 'pending'},
                        'human_review': {'status': 'pending'}}},
                    evidence=[{'passage_id': 'passage', 'textbook_id': BOOK}])
        self.assertEqual(validate_draft(data)['status'], 'needs_revision')
        data['screening']['stages']['duplicates']['status']='pass'
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
