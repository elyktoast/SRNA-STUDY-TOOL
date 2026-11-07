"""No-network tests for revision persistence safety gates."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from item_draft_revision_storage_v2 import digest,save_revision

OWNER="c003287a-10ce-4cc9-926e-ef7c3a162a26"
DRAFT="abc90a93-41f8-4d7c-8e27-94a609135572"

class Tests(unittest.TestCase):
    def test_digest_independent_of_object_key_order(self):
        self.assertEqual(digest({"a":1,"b":2}),digest({"b":2,"a":1}))
        self.assertNotEqual(digest({"a":1}),digest({"a":2}))
    def test_rejects_bad_parent_digest_before_database_access(self):
        with self.assertRaisesRegex(ValueError,"Expected parent digest"):
            save_revision(None,owner_uid=OWNER,draft_id=DRAFT,
                expected_parent_sha256="bad",reviewer_notes="Checked")
    def test_rejects_blank_review_notes_before_database_access(self):
        with self.assertRaisesRegex(ValueError,"Reviewer notes required"):
            save_revision(None,owner_uid=OWNER,draft_id=DRAFT,
                expected_parent_sha256="a"*64,reviewer_notes=" ")
    def test_rejects_untrusted_identity(self):
        with self.assertRaises(ValueError):
            save_revision(None,owner_uid="not-an-id",draft_id=DRAFT,
                expected_parent_sha256="a"*64,reviewer_notes="Checked")

if __name__=="__main__":unittest.main()
