"""Bounded HTTPS transport for opt-in staging question generation.

No logging, automatic retries, credential persistence or network activity on
import. Caller must use an approved endpoint and explicitly invoke the adapter.
"""
import json
import urllib.error
import urllib.request
from urllib.parse import urlsplit

class TransportError(RuntimeError):
    pass

def make_transport(*, allowed_hosts, timeout_seconds=25, max_response_bytes=262144):
    hosts = frozenset(allowed_hosts)
    if not hosts or any(not isinstance(h, str) or not h or "/" in h or ":" in h for h in hosts):
        raise ValueError("Explicit provider host allowlist required")
    if type(timeout_seconds) not in (int, float) or not 1 <= timeout_seconds <= 60:
        raise ValueError("Timeout must be 1-60 seconds")
    if type(max_response_bytes) is not int or not 1024 <= max_response_bytes <= 1048576:
        raise ValueError("Response limit must be 1 KiB to 1 MiB")

    def transport(*, endpoint, headers, body):
        url = urlsplit(endpoint)
        if url.scheme != "https" or url.hostname not in hosts or url.username or url.password or url.fragment or url.port not in (None, 443):
            raise TransportError("Provider endpoint not allowed")
        if not isinstance(headers, dict) or not isinstance(body, dict):
            raise TransportError("Invalid request")
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if len(encoded) > 524288:
            raise TransportError("Request exceeds 512 KiB")
        req = urllib.request.Request(endpoint, data=encoded, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout_seconds) as response:
                if response.geturl() != endpoint:
                    raise TransportError("Redirected provider response prohibited")
                raw = response.read(max_response_bytes + 1)
                if len(raw) > max_response_bytes:
                    raise TransportError("Provider response too large")
                return json.loads(raw.decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, UnicodeError, ValueError) as exc:
            # Never include provider error bodies, source text, or credentials.
            raise TransportError("Provider transport failed or returned invalid JSON") from None
    return transport
