"""Short-lived, source-bound staging image-delivery challenge.

A challenge is a server-issued proof of the exact page response prepared for
the authenticated reviewer, NOT proof that a human looked at the page. The
reviewer must explicitly acknowledge inspection in a separate authenticated
request. This module never grants approval or writes a nonce.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time

CHALLENGE_TTL_SECONDS = 120
DOMAIN = b"srna-staging-page-delivery-v2:"


def _encode(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode(value):
    if not isinstance(value, str) or not 0 < len(value) <= 4096:
        raise ValueError("Invalid delivery challenge")
    return base64.b64decode(value + "=" * (-len(value) % 4),
                            altchars=b"-_", validate=True)


def issue_delivery_challenge(secret, *, reviewer_uid, page, now=None):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Strong signing key required")
    if not isinstance(page, dict) or page.get("owner_uid") != reviewer_uid:
        raise ValueError("Page owner mismatch")
    from source_review_receipts_v2 import _validate
    _validate(reviewer_uid, page["owner_uid"], page["source_sha256"],
              page["r2_key"], page["pdf_page"])
    digest = page.get("image_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid image digest")
    payload = {"v": 2, "reviewer_uid": reviewer_uid,
               "owner_uid": page["owner_uid"],
               "source_sha256": page["source_sha256"],
               "r2_key": page["r2_key"], "pdf_page": page["pdf_page"],
               "image_sha256": digest,
               "iat": int(time.time() if now is None else now),
               "challenge_id": secrets.token_hex(16)}
    encoded = _encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    signature = _encode(hmac.new(secret, DOMAIN + encoded.encode(), hashlib.sha256).digest())
    return encoded + "." + signature


def verify_delivery_challenge(secret, challenge, *, reviewer_uid, page, now=None):
    if not isinstance(secret, bytes) or len(secret) < 32 or not isinstance(challenge, str):
        raise ValueError("Invalid delivery challenge")
    try:
        encoded, signature = challenge.split(".")
        expected = hmac.new(secret, DOMAIN + encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_decode(signature), expected):
            raise ValueError("Invalid delivery signature")
        payload = json.loads(_decode(encoded))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValueError("Invalid delivery challenge") from exc
    expected_fields = {"v": 2, "reviewer_uid": reviewer_uid,
                       "owner_uid": page.get("owner_uid"),
                       "source_sha256": page.get("source_sha256"),
                       "r2_key": page.get("r2_key"),
                       "pdf_page": page.get("pdf_page"),
                       "image_sha256": page.get("image_sha256")}
    if not isinstance(payload, dict) or set(payload) != set(expected_fields) | {"iat", "challenge_id"}:
        raise ValueError("Invalid delivery fields")
    if any(type(payload.get(k)) is not type(v) or payload.get(k) != v
           for k, v in expected_fields.items()):
        raise ValueError("Delivery challenge source or reviewer mismatch")
    current = int(time.time() if now is None else now)
    if (type(payload["iat"]) is not int or payload["iat"] > current
            or current - payload["iat"] > CHALLENGE_TTL_SECONDS):
        raise ValueError("Delivery challenge expired")
    challenge_id = payload["challenge_id"]
    if (not isinstance(challenge_id, str) or len(challenge_id) != 32
            or any(c not in "0123456789abcdef" for c in challenge_id)):
        raise ValueError("Invalid delivery challenge id")
    return challenge_id
