"""Bounded HTTPS transport for opt-in staging question generation.

No logging, automatic retries, credential persistence or network activity on
import. Caller must use an approved endpoint and explicitly invoke the adapter.
"""
import json
import hmac
import hashlib
import time
import urllib.error
import urllib.request
from urllib.parse import urlsplit

class TransportError(RuntimeError):
    def __init__(self, rule='PROVIDER_TRANSPORT', retry_after_seconds=None, remaining_requests=None, remaining_tokens=None):
        self.rule = rule
        self.retry_after_seconds = retry_after_seconds if type(retry_after_seconds) is int and 0 <= retry_after_seconds <= 3600 else None
        self.remaining_requests = remaining_requests if type(remaining_requests) is int and 0 <= remaining_requests <= 1000000000 else None
        self.remaining_tokens = remaining_tokens if type(remaining_tokens) is int and 0 <= remaining_tokens <= 1000000000 else None
        super().__init__('Provider transport unavailable')

class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise TransportError("PROVIDER_REDIRECT")


def make_transport(*, allowed_hosts, timeout_seconds=25, max_response_bytes=262144,
                   relay_url=None, relay_secret=None):
    hosts = frozenset(allowed_hosts)
    if not hosts or any(not isinstance(h, str) or not h or "/" in h or ":" in h for h in hosts):
        raise ValueError("Explicit provider host allowlist required")
    if type(timeout_seconds) not in (int, float) or not 1 <= timeout_seconds <= 60:
        raise ValueError("Timeout must be 1-60 seconds")
    if type(max_response_bytes) is not int or not 1024 <= max_response_bytes <= 1048576:
        raise ValueError("Response limit must be 1 KiB to 1 MiB")

    if (relay_url is None) != (relay_secret is None):
        raise ValueError('Relay URL and signing secret must be configured together')
    if relay_url is not None:
        parsed = urlsplit(relay_url)
        if (parsed.scheme != 'https' or parsed.hostname != 'reviewer-relay-staging.srnastudytool.com'
                or parsed.path != '/internal/groq-relay' or parsed.query or parsed.fragment
                or parsed.port not in (None, 443) or parsed.username or parsed.password
                or not isinstance(relay_secret, str) or len(relay_secret) < 32):
            raise ValueError('Invalid staging relay configuration')
    opener = urllib.request.build_opener(_NoRedirect())

    def transport(*, endpoint, headers, body):
        url = urlsplit(endpoint)
        if url.scheme != "https" or url.hostname not in hosts or url.username or url.password or url.fragment or url.port not in (None, 443) or url.query:
            raise TransportError("PROVIDER_ENDPOINT")
        if not isinstance(headers, dict) or not isinstance(body, dict):
            raise TransportError("PROVIDER_REQUEST")
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        if len(encoded) > 524288:
            raise TransportError("PROVIDER_REQUEST_SIZE")
        if relay_url is not None:
            stamp = str(int(time.time()))
            signed = b'srna-groq-relay-v1\n' + stamp.encode() + b'\n' + encoded
            signature = hmac.new(relay_secret.encode(), signed, hashlib.sha256).hexdigest()
            target = relay_url
            request_headers = {'Content-Type': 'application/json',
                               'X-Relay-Timestamp': stamp, 'X-Relay-Signature': signature,
                               'User-Agent': 'SRNA-Study-Tool-Staging-Relay/1.0',
                               'Accept': 'application/json'}
        else:
            target = endpoint
            request_headers = headers
        req = urllib.request.Request(target, data=encoded, headers=request_headers, method="POST")
        try:
            with opener.open(req, timeout=timeout_seconds) as response:
                if response.geturl() != target:
                    raise TransportError("PROVIDER_REDIRECT")
                raw = response.read(max_response_bytes + 1)
                if len(raw) > max_response_bytes:
                    raise TransportError("PROVIDER_RESPONSE_SIZE")
                return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as exc:
            # Never inspect provider response bodies or log credentials.
            status = exc.code
            if relay_url is not None:
                try:
                    diagnostic = json.loads(exc.read(2048).decode('utf-8'))
                except (ValueError, UnicodeError):
                    diagnostic = {}
                if diagnostic.get('error') in ('invalid_json', 'invalid_step', 'invalid_provider_payload'):
                    raise TransportError('RELAY_PAYLOAD') from None
                if diagnostic.get('error') == 'method_not_allowed':
                    raise TransportError('RELAY_METHOD') from None
                if diagnostic.get('error') == 'request_too_large':
                    raise TransportError('RELAY_SIZE') from None
                if diagnostic.get('error') == 'forbidden':
                    raise TransportError('RELAY_AUTH') from None
                if diagnostic.get('error') == 'provider_failed':
                    allowed = {'PROVIDER_AUTH', 'PROVIDER_FORBIDDEN', 'PROVIDER_RATE_LIMIT', 'PROVIDER_UPSTREAM'}
                    raise TransportError(diagnostic.get('rule') if diagnostic.get('rule') in allowed else 'RELAY_UPSTREAM', diagnostic.get('retry_after_seconds'), diagnostic.get('remaining_requests'), diagnostic.get('remaining_tokens')) from None
                if diagnostic.get('error') in ('relay_network', 'relay_disabled'):
                    raise TransportError('RELAY_UNAVAILABLE') from None
                # A response from our Worker always carries X-Review-Approval-Enabled.
                # A 403 without that header was generated before the Worker handler.
                if status == 403 and exc.headers.get('X-Review-Approval-Enabled') != 'false':
                    raise TransportError('RELAY_EDGE_403') from None
                safe_status = status if status in (400, 401, 403, 404, 405, 413, 429, 500, 502, 503, 504) else 0
                raise TransportError('RELAY_HTTP_' + str(safe_status)) from None
            rule = ('PROVIDER_AUTH' if status == 401 else
                    'PROVIDER_FORBIDDEN' if status == 403 else
                    'PROVIDER_RATE_LIMIT' if status == 429 else
                    'PROVIDER_REQUEST_REJECTED' if status in (400, 404, 413, 422) else
                    'PROVIDER_UPSTREAM' if status >= 500 else 'PROVIDER_HTTP_OTHER')
            raise TransportError(rule) from None
        except (TimeoutError, __import__('socket').timeout):
            raise TransportError('PROVIDER_TIMEOUT') from None
        except urllib.error.URLError as exc:
            # A socket timeout can be wrapped in URLError.
            import socket
            rule = 'PROVIDER_TIMEOUT' if isinstance(exc.reason, (TimeoutError, socket.timeout)) else 'PROVIDER_NETWORK'
            raise TransportError(rule) from None
        except (UnicodeError, ValueError):
            raise TransportError('PROVIDER_INVALID_JSON') from None
    return transport
