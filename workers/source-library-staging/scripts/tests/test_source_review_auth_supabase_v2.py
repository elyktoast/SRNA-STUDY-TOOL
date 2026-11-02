import io
import unittest
from urllib.error import HTTPError, URLError
from source_review_auth_supabase_v2 import SupabaseAuthProvider

UID = "d7c8ad4c-673d-4d87-a122-7d9bff4451bb"

class Response(io.BytesIO):
    def __enter__(self): return self
    def __exit__(self, *args): self.close()

class SupabaseAuthTests(unittest.TestCase):
    def test_verified_user_and_request(self):
        calls = []
        def opener(req, timeout):
            calls.append((req, timeout))
            return Response(('{"id":"' + UID + '","user_metadata":{"role":"admin"}}').encode())
        provider = SupabaseAuthProvider("https://example.supabase.co", "public-key", opener=opener)
        self.assertEqual(provider.get_user("token"), {"id": UID, "active": True})
        req, timeout = calls[0]
        self.assertEqual(req.full_url, "https://example.supabase.co/auth/v1/user")
        self.assertEqual(req.get_header("Authorization"), "Bearer token")
        self.assertEqual(req.get_header("Apikey"), "public-key")
        self.assertEqual(timeout, 10)
    def test_invalid_credentials_fail_closed(self):
        for payload in (b'{}', b'[]', b'{"id":null}', b'not-json'):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                SupabaseAuthProvider("https://example.supabase.co", "key",
                    opener=lambda req, timeout: Response(payload)).get_user("token")
    def test_auth_errors_fail_closed(self):
        def broken(req, timeout): raise URLError("unavailable")
        with self.assertRaises(ValueError):
            SupabaseAuthProvider("https://example.supabase.co", "key", opener=broken).get_user("token")
    def test_invalid_origin_and_token(self):
        for origin in ("http://example.com", "https://user@example.com", "https://example.com/other"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                SupabaseAuthProvider(origin, "key")
        provider = SupabaseAuthProvider("https://example.supabase.co", "key")
        with self.assertRaises(ValueError): provider.get_user(" token ")

if __name__ == "__main__":
    unittest.main()
