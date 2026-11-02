import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from chapter_review import review_fingerprint
from approved_chapter_plan import build_plan

GROUPS = [
 {"first_page": 20, "last_page": 21, "candidates": [
     {"pdf_page": 20, "heading": "Running header", "detector": "layout"},
     {"pdf_page": 21, "heading": "Airway", "detector": "text"}]},
 {"first_page": 65, "last_page": 65, "candidates": [
     {"pdf_page": 65, "heading": "Airway equipment", "detector": "layout"}]}]
def packet():
 return {"schema_version": 2, "review_fingerprint": review_fingerprint(GROUPS),
         "decisions": [{"group": 1, "decision": "Chapter", "notes": ""},
                       {"group": 2, "decision": "Subsection", "notes": ""}]}
def picks():
 return [{"group": 1, "candidate_index": 1}, {"group": 2, "candidate_index": 0}]

class PlanTests(unittest.TestCase):
 def test_explicit_selection_prepares_no_write(self):
  result = build_plan(GROUPS, packet(), picks(), 420)
  self.assertEqual([s["start_page"] for s in result["sections"]], [21, 65])
  self.assertEqual(result["sections"][0]["heading"], "Airway")
  self.assertFalse(result["database_written"])
  self.assertFalse(result["citation_verified"])

 def test_reject_missing_selection(self):
  with self.assertRaises(ValueError):
   build_plan(GROUPS, packet(), picks()[:1], 420)

 def test_reject_stale_review(self):
  data = packet()
  data["review_fingerprint"] = "0" * 64
  with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
   build_plan(GROUPS, data, picks(), 420)

 def test_reject_page_out_of_range(self):
  with self.assertRaises(ValueError):
   build_plan(GROUPS, packet(), picks(), 40)

 def test_subsection_requires_chapter(self):
  data = packet()
  data["decisions"][0]["decision"] = "Reject"
  with self.assertRaisesRegex(ValueError, "Subsection requires"):
   build_plan(GROUPS, data, picks()[1:], 420)

if __name__ == "__main__":
 unittest.main()
