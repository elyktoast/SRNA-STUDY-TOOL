"""Offline contract tests for safe rate-limit propagation."""
import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from item_ai_https_transport_v2 import make_transport, TransportError


class RateLimitTransportTests(unittest.TestCase):
    def test_relay_retry_delay_is_bounded(self):
        transport = make_transport(allowed_hosts=["api.groq.com"],
            relay_url="https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
            relay_secret="a" * 40)
        error = HTTPError("https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay",
            502, "Bad Gateway", {}, io.BytesIO(json.dumps({
                "error": "provider_failed", "rule": "PROVIDER_RATE_LIMIT",
                "retry_after_seconds": 60}).encode()))
        with patch("urllib.request.OpenerDirector.open", side_effect=error):
            with self.assertRaises(TransportError) as caught:
                transport(endpoint="https://api.groq.com/openai/v1/chat/completions",
                          headers={}, body={"messages": []})
        self.assertEqual(caught.exception.rule, "PROVIDER_RATE_LIMIT")
        self.assertEqual(caught.exception.retry_after_seconds, 60)

    def test_invalid_delay_is_ignored(self):
        self.assertIsNone(TransportError("PROVIDER_RATE_LIMIT", 3601).retry_after_seconds)
        self.assertIsNone(TransportError("PROVIDER_RATE_LIMIT", "60").retry_after_seconds)
        self.assertEqual(TransportError("PROVIDER_RATE_LIMIT", 0).retry_after_seconds, 0)


if __name__ == "__main__":
    unittest.main()
