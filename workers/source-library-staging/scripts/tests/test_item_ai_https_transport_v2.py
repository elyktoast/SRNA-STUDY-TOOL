import io
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from item_ai_https_transport_v2 import make_transport, TransportError

class FakeResponse:
    def __init__(self, data, url="https://api.example.test/v1/chat"):
        self.data, self.url = data, url
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, n):
        return self.data[:n]
    def geturl(self):
        return self.url

class TransportTests(unittest.TestCase):
    def setUp(self):
        self.transport = make_transport(allowed_hosts=["api.example.test"],
                                        timeout_seconds=5, max_response_bytes=1024)
    def call(self, endpoint="https://api.example.test/v1/chat"):
        return self.transport(endpoint=endpoint, headers={"Authorization": "Bearer test"},
                              body={"model": "test"})
    def test_blocks_other_host(self):
        with self.assertRaises(TransportError):
            self.call("https://evil.example/v1/chat")
    def test_parses_bounded_json(self):
        with patch("item_ai_https_transport_v2.urllib.request.urlopen",
                   return_value=FakeResponse(b'{"choices":[]}')):
            self.assertEqual(self.call(), {"choices": []})
    def test_rejects_oversized_response(self):
        with patch("item_ai_https_transport_v2.urllib.request.urlopen",
                   return_value=FakeResponse(b"x" * 1025)):
            with self.assertRaises(TransportError):
                self.call()
    def test_rejects_redirect(self):
        with patch("item_ai_https_transport_v2.urllib.request.urlopen",
                   return_value=FakeResponse(b"{}", "https://api.example.test/redirect")):
            with self.assertRaises(TransportError):
                self.call()
    def test_requires_allowlist(self):
        with self.assertRaises(ValueError):
            make_transport(allowed_hosts=[])

if __name__ == "__main__":
    unittest.main()
