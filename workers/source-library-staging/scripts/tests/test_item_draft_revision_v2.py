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
    def test_concept_relevance_revision_preserves_original_identity_and_evidence(self):
        draft,passages=fixture()
        draft["question"]["concept_card"]={"relevance":"Unsupported policy", "evidence_ids":[PASSAGE]}
        result=propose_revision(draft,passages,question_edits={"concept_card":{"relevance":"Source-grounded clinical importance"}})
        self.assertEqual(result["question"]["concept_card"]["relevance"],"Source-grounded clinical importance")
        self.assertEqual(draft["question"]["concept_card"]["relevance"],"Unsupported policy")
        self.assertEqual(result["question"]["concept_card"]["evidence_ids"],[PASSAGE])
        self.assertEqual(result["question"]["key"],draft["question"]["key"])
        self.assertFalse(result["can_publish"])
        self.assertTrue(result["requires_clinical_review"])

    def test_concept_revision_cannot_change_evidence_or_other_fields(self):
        draft,passages=fixture(); draft["question"]["concept_card"]={"relevance":"Original","evidence_ids":[PASSAGE]}
        for edit in ({"evidence_ids":["forged"]},{"relevance":"New","objective":"forged"},{"relevance":""},{"relevance":"x"*2001}):
            with self.subTest(edit=edit),self.assertRaises(ValueError):
                propose_revision(draft,passages,question_edits={"concept_card":edit})

    def test_source_explanation_corrections_are_append_only_and_cannot_change_identity(self):
        from copy import deepcopy
        draft, passages = fixture()
        draft["question"]["concept_card"] = {"mechanism":"Unsupported receptor mechanism",
            "relevance":"Original relevance", "counterfactual":"Overbroad claim",
            "misconception":"Original misconception", "evidence_ids":[PASSAGE], "objective":"III.H.4"}
        draft["question"]["rationale"] = {"core_concept":"Overbroad only claim",
            "why_key_wins":"Original answer explanation", "trap":"Original trap"}
        original = deepcopy(draft)
        proposal = propose_revision(draft, passages, question_edits={
            "concept_card":{"mechanism":"The indexed source recommends awake extubation.",
                            "counterfactual":"The alternative does not match the cited recommendation."},
            "rationale":{"core_concept":"The source supports awake extubation."}})
        self.assertEqual(draft, original)
        revised = proposal["question"]
        for field in ("key", "options", "evidence"):
            self.assertEqual(revised[field], original["question"][field])
        self.assertEqual(revised["concept_card"]["evidence_ids"], [PASSAGE])
        self.assertEqual(revised["concept_card"]["objective"], "III.H.4")
        self.assertEqual(revised["rationale"]["core_concept"], "The source supports awake extubation.")
        self.assertFalse(proposal["can_publish"])
        self.assertTrue(proposal["requires_clinical_review"])
        for edits in ({"rationale":{"key":["B"]}}, {"rationale":{"core_concept":""}},
                      {"concept_card":{"mechanism":True}}, {"rationale":{"trap":"x"*2001}},
                      {"concept_card":{"evidence_ids":["forged"]}}):
            with self.subTest(edits=edits), self.assertRaises(ValueError):
                propose_revision(draft, passages, question_edits=edits)

    def test_quote_correction_does_not_mutate_saved_question(self):
        draft,passages=fixture()
        result=propose_revision(draft,passages,citation_excerpts={0:"Awake extubation is recommended."})
        self.assertEqual(result["question"]["evidence"][0]["excerpt"],passages[0]["excerpt"])
        self.assertNotIn("excerpt",draft["question"]["evidence"][0])
        self.assertFalse(result["saved"])
        self.assertFalse(result["can_publish"])
        self.assertFalse(result["database_writes"])
    def test_accepts_json_string_citation_index(self):
        draft,passages=fixture()
        result=propose_revision(draft,passages,citation_excerpts={"0":"Awake extubation is recommended."})
        self.assertEqual(result["question"]["evidence"][0]["excerpt"],passages[0]["excerpt"])
    def test_rejects_noncanonical_citation_index(self):
        draft,passages=fixture()
        for index in ("00","-1","1.0","０", "1e0"):
            with self.subTest(index=index),self.assertRaisesRegex(ValueError,"Invalid citation correction"):
                propose_revision(draft,passages,citation_excerpts={index:"Awake extubation is recommended."})
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

    def test_rejects_answer_key_and_unrecognized_edits(self):
        draft,passages=fixture()
        for edits in ({"key":["B"]},{"rationale":"unsupported"},{"options":{"C":"new"}}):
            with self.subTest(edits=edits),self.assertRaises(ValueError):
                propose_revision(draft,passages,question_edits=edits)
    def test_rejects_empty_stem_and_option_text(self):
        draft,passages=fixture()
        draft["question"]["stem"]="Which approach?"
        for edits in ({"stem":"  "},{"options":{"A":""}}):
            with self.subTest(edits=edits),self.assertRaises(ValueError):
                propose_revision(draft,passages,question_edits=edits)
    def test_text_edits_do_not_mutate_original(self):
        draft,passages=fixture()
        draft["question"]["stem"]="Original question"
        proposal=propose_revision(draft,passages,question_edits={"stem":"Revised question","options":{"A":"Fully awake"}})
        self.assertEqual(proposal["question"]["stem"],"Revised question")
        self.assertEqual(proposal["question"]["options"][0]["text"],"Fully awake")
        self.assertEqual(draft["question"]["stem"],"Original question")
        self.assertEqual(draft["question"]["options"][0]["text"],"Awake")
        self.assertFalse(proposal["can_publish"])

if __name__=="__main__": unittest.main()
