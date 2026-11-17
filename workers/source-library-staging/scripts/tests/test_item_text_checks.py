import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_text_checks import check

class EditorialTests(unittest.TestCase):
    def test_rationale_inside_a_result_choice_is_flagged_without_an_intervention_verb(self):
        item={'format':'MC','key':['A'],'options':[
            {'id':'A','text':'Poor, because the stated environment changes the drug fraction'},
            {'id':'B','text':'Favorable result'}, {'id':'C','text':'Unchanged result'}, {'id':'D','text':'Other result'}]}
        self.assertIn('R-6.9',{issue['rule_id'] for issue in check(item)})
        item['options'][0]['text']='Reduced receptor activation'
        self.assertNotIn('R-6.9',{issue['rule_id'] for issue in check(item)})

    def test_short_multiword_drug_name_is_not_a_length_cue_when_visibly_shorter(self):
        item={"format":"MC","key":["C"],"options":[{"id":"A","text":"Desflurane"},
              {"id":"B","text":"Succinylcholine"},{"id":"C","text":"Nitrous oxide"},
              {"id":"D","text":"Isoflurane"}]}
        self.assertNotIn("R-6.8",{i["rule_id"] for i in check(item)})

    def test_actually_longer_short_key_still_flags(self):
        item={"format":"MC","key":["A"],"options":[{"id":"A","text":"Substantially longer explanation"},
              {"id":"B","text":"Small option"},{"id":"C","text":"Other choice"}]}
        self.assertIn("R-6.8",{i["rule_id"] for i in check(item)})

    def test_length(self):
        item = {"format": "MC", "key": ["A"], "stem": "Question?",
                "options": [{"id": k, "text": t} for k,t in zip("ABCD",
                ["A substantially longer explanation than others", "Other", "Third", "Fourth"])]}
        self.assertIn("R-6.8", {e["rule_id"] for e in check(item)})
    def test_verbatim_overlap(self):
        item = {"format": "MC", "key": ["A"],
                "stem": "One two three four five six seven eight nine?",
                "options": [{"id": k, "text": t} for k,t in zip("ABCD", ["Alpha", "Beta", "Gamma", "Delta"])]}
        self.assertIn("R-2.8", {e["rule_id"] for e in check(item,
                      ["one two three four five six seven eight nine ten"])})
    def test_overlap_diagnostic_locates_stem_words_without_echoing_source(self):
        source='one two three four five six seven eight'
        item={'format':'MC','key':['A'],'stem':'Prefix: ONE, two three four five six seven eight?',
              'options':[{'id':'A','text':'Different result'}]}
        issue=next(i for i in check(item,[source]) if i['rule_id']=='R-2.8')
        self.assertEqual((issue['field'],issue['word_start'],issue['word_count']),('stem',1,8))
        self.assertNotIn(source,str(issue))

    def test_overlap_diagnostic_locates_option_without_scanning_cited_quotations(self):
        source='one two three four five six seven eight'
        item={'format':'MC','key':['A'],'stem':'Which response?',
              'options':[{'id':'A','text':'Different response'}, {'id':'B','text':source}]}
        issue=next(i for i in check(item,[source]) if i['rule_id']=='R-2.8')
        self.assertEqual((issue['field'],issue['word_start']),('options.1.text',0))
        item['options'][1]['text']='Another result';item['evidence']=[{'excerpt':source}]
        self.assertNotIn('R-2.8',{i['rule_id'] for i in check(item,[source])})

    def test_no_overlap(self):
        item = {"format": "MC", "key": ["A"], "stem": "Which value?",
                "options": [{"id": k, "text": t} for k,t in zip("ABCD", ["One", "Two", "Three", "Four"])]}
        self.assertEqual(check(item), [])

if __name__ == "__main__":
    unittest.main()
