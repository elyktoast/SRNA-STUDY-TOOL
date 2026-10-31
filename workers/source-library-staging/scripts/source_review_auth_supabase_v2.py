"""Staging-only Supabase Auth user validation adapter.

Uses Supabase Auth's /auth/v1/user endpoint rather than decoding JWT claims.
Call only on a trusted server. Session revocation requires an additional
server-side auth.sessions check where immediate revocation is required.
"""
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.parse import urlparse


class SupabaseAuthProvider:
    def __init__(self, supabase_url, publishable_key, *, opener=urlopen):
        parsed = urlparse(supabase_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise ValueError("Valid HTTPS Supabase project origin required")
        if not isinstance(publishable_key, str) or not publishable_key.strip():
            raise ValueError("Supabase API key required")
        self.origin = supabase_url.rstrip("/")
        self.api_key = publishable_key
        self.opener = opener

    def get_user(self, access_token):
        if not isinstance(access_token, str) or not access_token or access_token != access_token.strip():
            raise ValueError("Valid bearer token required")
        request = Request(
            self.origin + "/auth/v1/user",
            headers={"apikey": self.api_key, "Authorization": "Bearer " + access_token,
                     "Accept": "application/json"},
            method="GET",
        )
        try:
            with self.opener(request, timeout=10) as response:
                payload = json.load(response)
        except (HTTPError, URLError, OSError, ValueError) as exc:
            raise ValueError("Supabase authentication verification failed") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise ValueError("Supabase returned invalid user identity")
        # Supabase /user is authoritative for identity; never authorize using
        # user_metadata, app_metadata, or caller-provided JWT claims.
        return {"id": payload["id"], "active": True}
