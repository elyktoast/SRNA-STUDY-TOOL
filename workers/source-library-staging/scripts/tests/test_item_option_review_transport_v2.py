import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_ai_https_transport_v2 import TransportError
from item_option_review_transport_v2 import request_judgments


class OptionReviewTransportTests(unittest.TestCase):
    def setUp(self):
        self.payload = {"format": "MC", "stem": "Example?", "options": [
            {"id": choice, "text": f"Choice {choice}"} for choice in "ABCD"],
            "retrieval": {"option_audits": [{"option_id": choice, "retrieved_passage_ids": [choice]}
                                            for choice in "ABCD"]},
            "source_passages": [{"passage_id": choice} for choice in "ABCD"]}

    def test_oversize_rejection_reuses_blinded_context_and_limits_sources_per_option(self):
        adapter = Mock(side_effect=[TransportError("PROVIDER_REQUEST_SIZE"), *[
            {"judgments": [{"option_id": choice}]} for choice in "ABCD"]])
        result = request_judgments(self.payload, adapter)
        self.assertEqual(result, {"judgments": [{"option_id": choice} for choice in "ABCD"]})
        for choice, call in zip("ABCD", adapter.call_args_list[1:]):
            request = call.args[0]
            self.assertEqual(request["target_option"], choice)
            self.assertEqual(request["options"], self.payload["options"])
            self.assertEqual(request["stem"], self.payload["stem"])
            self.assertEqual(request["source_passages"], [{"passage_id": choice}])
            self.assertIs(request["blind"], True)
            self.assertNotIn("key", request)

    def test_a_provider_failure_does_not_split_or_repeat_valid_judgments(self):
        adapter = Mock(side_effect=TransportError("PROVIDER_UPSTREAM"))
        with self.assertRaises(TransportError):
            request_judgments(self.payload, adapter)
        self.assertEqual(adapter.call_count, 1)
        adapter = Mock(side_effect=[TransportError("PROVIDER_REQUEST_SIZE"),
                                    {"judgments": [{"option_id": "A"}]},
                                    TransportError("PROVIDER_TIMEOUT")])
        with self.assertRaises(TransportError):
            request_judgments(self.payload, adapter)
        self.assertEqual(adapter.call_count, 3)
