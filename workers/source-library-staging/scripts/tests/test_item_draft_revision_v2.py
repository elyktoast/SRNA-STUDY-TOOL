"""No-network tests for immutable evidence revision proposals."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_draft_revision_v2 import propose_revision

BOOK="2a589498-aaa4-410f-b51a-00d3ab99eafd"
PASSAGE="0e5e0c56-9c30-4c6d-8aef-4329446b198c"

def fixture():
    item={"format":"MC","evidence":[{"passage_id":PASSAGE,"textbook_id":BOOK,"pdf_page":197}],
          "options":[{"id":"A","text":"Awake"},{"id":"B","text":"Deep"}],"key":["A"]}
    draft={"draft_id":"draft-1","published":False,"status":"pending_review","question":item}
    passages=[{"passage_id":PASSAGE,"textbook_id":BOOK,"pdf_page_start":197,
               "excerpt":"Awake extubation is recommended."}]
    return draft,passages

class RevisionTests(unittest.TestCase):
    def test_quote_correction_does_not_mutate_saved_question(self):
        draft,passages=fixture()
        result=propose_revision(draft,passages,citation_excerpts={0:"Awake extubation is recommended."})
        self.assertEqual(result["question"]["evidence"][0]["excerpt"],passages[0]["excerpt"])
        self.assertNotIn("excerpt",draft["question"]["evidence"][0])
        self.assertFalse(result["saved"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])
    def test_refuses_invented_quote(self):
        draft,passages=fixture()
        with self.assertRaisesRegex(ValueError,"must match indexed"):
            propose_revision(draft,passages,citation_excerpts={0:"Deep extubation always safe."})
    def test_requires_every_option_evidence(self):
        draft,passages=fixture()
        with self.assertRaisesRegex(ValueError,"Every option"):
            propose_revision(draft,passages,option_evidence={"A":{"verdict":"supports_key","passage_ids":[PASSAGE],"explanation":"Text supports awake extubation."}})
    def test_refuses_unindexed_option_passage(self):
        draft,passages=fixture()
        evidence={"A":{"verdict":"supports_key","passage_ids":["unknown"],"explanation":"Because"},
                  "B":{"verdict":"refutes_distractor","passage_ids":[PASSAGE],"explanation":"Because"}}
        with self.assertRaisesRegex(ValueError,"incomplete or unindexed"):
            propose_revision(draft,passages,option_evidence=evidence)
    def test_rejects_finalized(self):
        draft,passages=fixture()
        draft["status"]="approved_for_bank"
        with self.assertRaisesRegex(ValueError,"Only unpublished"):
            propose_revision(draft,passages)

if __name__=="__main__": unittest.main()
