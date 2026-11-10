import copy
import json
import unittest
from item_ai_provider_v2 import make_adapter
from item_source_quote_spans_v2 import prepare, hydrate


class SourceQuoteSpanTests(unittest.TestCase):
    def test_short_negations_are_preserved_as_source_context(self):
        request={"source_passages":[{"passage_id":"p1","excerpt":"No\ntriggering drugs.\nNever\nignore this warning."}]}
        packet, lookup=prepare(request)
        self.assertEqual([s["text"] for s in packet["source_passages"][0]["quote_spans"]],
                         ["No","triggering drugs.","Never","ignore this warning."])
        self.assertEqual(lookup["p1"]["q0"],"No")

    def setUp(self):
        self.request = {"step":"option_review", "rules_version":"2.0", "auto_publish":False,
            "blind":True, "format":"MC", "stem":"Which is a trigger?",
            "options":[{"id":"A","text":"Volatile agent"},{"id":"B","text":"Local anesthetic"}],
            "retrieval":{"option_audits":[{"option_id":"A","retrieved_passage_ids":["p1"]},
                                         {"option_id":"B","retrieved_passage_ids":["p2"]}]},
            "source_passages":[{"passage_id":"p1","excerpt":"Triggering (Unsafe) Agents\nSevoﬂurane is listed."},
                               {"passage_id":"p2","excerpt":"Nontriggering (Safe) Agents\nLocal anesthetics."}],
            "task":"independent_option_adjudication"}
        self.response = {"judgments":[{"option_id":"A","verdict":"refutes_distractor",
            "passage_ids":["p1"],"quote_refs":[{"passage_id":"p1","span_id":"q1"}],
            "explanation":"An intentionally wrong verdict stays wrong.","source_conflict_found":False}]}

    def test_exact_source_text_restored_without_correcting_independent_verdict(self):
        original_request, original_response = copy.deepcopy(self.request), copy.deepcopy(self.response)
        packet, lookup = prepare(self.request)
        result = hydrate(self.response, self.request, lookup)
        self.assertEqual(result["judgments"][0]["quotes"], ["Sevoﬂurane is listed."])
        self.assertEqual(result["judgments"][0]["verdict"], "refutes_distractor")
        self.assertNotIn("quote_refs", result["judgments"][0])
        self.assertNotIn("excerpt", packet["source_passages"][0])
        self.assertEqual(self.request, original_request)
        self.assertEqual(self.response, original_response)

    def test_unknown_cross_option_and_uncited_spans_rejected(self):
        _, lookup = prepare(self.request)
        for ref in [{"passage_id":"p1","span_id":"missing"},
                    {"passage_id":"unknown","span_id":"q0"},
                    {"passage_id":"p2","span_id":"q0"}]:
            response = copy.deepcopy(self.response)
            response["judgments"][0]["quote_refs"] = [ref]
            with self.subTest(ref=ref), self.assertRaises(ValueError):
                hydrate(response, self.request, lookup)
        response = copy.deepcopy(self.response)
        response["judgments"][0]["passage_ids"] = []
        with self.assertRaises(ValueError):
            hydrate(response, self.request, lookup)

    def test_ambiguous_or_empty_quote_references_rejected(self):
        _, lookup = prepare(self.request)
        for refs in [[], None, [{"passage_id":"p1","span_id":"q0","text":"forged"}]]:
            response = copy.deepcopy(self.response)
            response["judgments"][0]["quote_refs"] = refs
            with self.subTest(refs=refs), self.assertRaises(ValueError):
                hydrate(response, self.request, lookup)
        response = copy.deepcopy(self.response)
        response["judgments"][0]["quotes"] = ["forged"]
        with self.assertRaises(ValueError):
            hydrate(response, self.request, lookup)

    def test_every_bounded_span_is_an_actual_contiguous_source_substring(self):
        self.request["source_passages"][0]["excerpt"] = "word " * 500
        packet, _ = prepare(self.request)
        for p, original in zip(packet["source_passages"], self.request["source_passages"]):
            self.assertEqual(len({s["id"] for s in p["quote_spans"]}), len(p["quote_spans"]))
            for span in p["quote_spans"]:
                self.assertTrue(1 <= len(span["text"]) <= 300)
                self.assertIn(span["text"], original["excerpt"])

    def test_adapter_uses_bounded_span_protocol_without_answer_leakage(self):
        calls = []
        def transport(**kwargs):
            calls.append(kwargs)
            return {"choices":[{"message":{"content":json.dumps(self.response)}}]}
        adapter = make_adapter(endpoint="https://provider.example/v1/chat/completions",
            api_key="test-secret",model="reviewer",transport=transport,owner_opt_in=True)
        result = adapter(self.request)
        sent = json.loads(calls[0]["body"]["messages"][1]["content"])
        self.assertEqual(calls[0]["body"]["max_tokens"], 1000)
        self.assertIn("quote_spans", sent["source_passages"][0])
        self.assertNotIn("key", sent)
        self.assertNotIn("expected_verdict", json.dumps(sent))
        self.assertNotIn("rationale", sent)
        self.assertEqual(result["judgments"][0]["quotes"], ["Sevoﬂurane is listed."])


if __name__ == "__main__":
    unittest.main()
