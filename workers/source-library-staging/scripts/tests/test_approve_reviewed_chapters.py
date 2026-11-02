import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chapter_review import review_fingerprint
from approve_reviewed_chapters import approve_reviewed_chapters

GROUPS = [{"first_page": 21, "last_page": 21, "candidates":
           [{"pdf_page": 21, "heading": "Airway", "detector": "layout"}]}]
OWNER = "c003287a-10ce-4cc9-926e-ef7c3a162a26"
BOOK = "810040fc-da03-4fa5-bcc0-78c25957c325"
def review():
 return {"schema_version": 2, "review_fingerprint": review_fingerprint(GROUPS),
         "decisions": [{"group": 1, "decision": "Chapter", "notes": ""}]}

class ApprovalTests(unittest.TestCase):
 def test_rebuilds_heading_from_trusted_candidates(self):
  with patch("approve_reviewed_chapters.apply_plan", return_value={"sections_applied": 1}) as apply:
   result = approve_reviewed_chapters(object(), OWNER, BOOK, GROUPS, review(),
                                      [{"group": 1, "candidate_index": 0}], 420)
   self.assertEqual(result["status"], "sections_assigned_unverified_citations")
   plan = apply.call_args.args[3]
   self.assertEqual(plan["sections"][0]["heading"], "Airway")
   self.assertEqual(plan["sections"][0]["start_page"], 21)

 def test_stale_review_never_reaches_db(self):
  data = review()
  data["review_fingerprint"] = "0" * 64
  with patch("approve_reviewed_chapters.apply_plan") as apply:
   with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
    approve_reviewed_chapters(object(), OWNER, BOOK, GROUPS, data,
                              [{"group": 1, "candidate_index": 0}], 420)
   apply.assert_not_called()

 def test_unselected_candidate_never_reaches_db(self):
  with patch("approve_reviewed_chapters.apply_plan") as apply:
   with self.assertRaises(ValueError):
    approve_reviewed_chapters(object(), OWNER, BOOK, GROUPS, review(),
                              [{"group": 1, "candidate_index": 5}], 420)
   apply.assert_not_called()

if __name__ == "__main__":
 unittest.main()
