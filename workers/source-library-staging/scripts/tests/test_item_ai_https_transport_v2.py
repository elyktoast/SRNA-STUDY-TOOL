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
    def test_requires_allowlist(self):
        with self.assertRaises(ValueError): make_transport(allowed_hosts=[])

if __name__ == "__main__":
    unittest.main()
