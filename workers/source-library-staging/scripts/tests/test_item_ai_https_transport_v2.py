import unittest
import sys
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_ai_https_transport_v2 import make_transport, TransportError, _NoRedirect

class FakeResponse:
    def __init__(self, data, url="https://api.example.test/v1/chat"):
        self.data, self.url = data, url
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return self.data[:n]
    def geturl(self): return self.url

class TransportTests(unittest.TestCase):
    def call(self, endpoint="https://api.example.test/v1/chat"):
        return self.transport(endpoint=endpoint, headers={"Authorization": "Bearer test"}, body={"model": "test"})
    def setup_transport(self, response):
        mock_opener = Mock()
        mock_opener.open.return_value = response
        with patch("item_ai_https_transport_v2.urllib.request.build_opener", return_value=mock_opener):
            self.transport = make_transport(allowed_hosts=["api.example.test"], timeout_seconds=5, max_response_bytes=1024)
        return mock_opener
    def test_blocks_other_host(self):
        opener = self.setup_transport(FakeResponse(b"{}"))
        with self.assertRaises(TransportError):
            self.call("https://evil.example/v1/chat")
        opener.open.assert_not_called()
    def test_rejects_query_string_before_network(self):
        opener = self.setup_transport(FakeResponse(b"{}"))
        with self.assertRaises(TransportError):
            self.call("https://api.example.test/v1/chat?token=secret")
        opener.open.assert_not_called()

    def test_parses_bounded_json(self):
        self.setup_transport(FakeResponse(b'{"choices":[]}'))
        self.assertEqual(self.call(), {"choices": []})
    def test_rejects_oversized_response(self):
        self.setup_transport(FakeResponse(b"x" * 1025))
        with self.assertRaises(TransportError): self.call()
    def test_rejects_redirected_response(self):
        self.setup_transport(FakeResponse(b"{}", "https://api.example.test/redirect"))
        with self.assertRaises(TransportError): self.call()
    def test_redirect_handler_blocks_before_following(self):
        with self.assertRaises(TransportError):
            _NoRedirect().redirect_request(None, None, 302, "Found", {}, "https://evil.example/")
    def test_provider_http_errors_are_classified_without_body(self):
        from urllib.error import HTTPError
        from io import BytesIO
        for status, rule in [(400, "PROVIDER_REQUEST_REJECTED"),
                             (401, "PROVIDER_AUTH"), (403, "PROVIDER_AUTH"),
                             (429, "PROVIDER_RATE_LIMIT"), (500, "PROVIDER_UPSTREAM")]:
            with self.subTest(status=status):
                opener = self.setup_transport(FakeResponse(b"{}"))
                opener.open.side_effect = HTTPError("https://api.example.test/v1/chat", status, "private", {}, BytesIO(b"secret response"))
                with self.assertRaises(TransportError) as ctx: self.call()
                self.assertEqual(ctx.exception.rule, rule)
                self.assertNotIn("secret", str(ctx.exception))

    def test_network_timeout_and_json_errors(self):
        from urllib.error import URLError
        import socket
        for failure, rule in [(URLError("unreachable"), "PROVIDER_NETWORK"),
                              (URLError(socket.timeout()), "PROVIDER_TIMEOUT"),
                              (TimeoutError(), "PROVIDER_TIMEOUT")]:
            with self.subTest(rule=rule):
                opener = self.setup_transport(FakeResponse(b"{}"))
                opener.open.side_effect = failure
                with self.assertRaises(TransportError) as ctx: self.call()
                self.assertEqual(ctx.exception.rule, rule)
        self.setup_transport(FakeResponse(b"not json"))
        with self.assertRaises(TransportError) as ctx: self.call()
        self.assertEqual(ctx.exception.rule, "PROVIDER_INVALID_JSON")

    def test_requires_allowlist(self):
        with self.assertRaises(ValueError): make_transport(allowed_hosts=[])

if __name__ == "__main__":
    unittest.main()
