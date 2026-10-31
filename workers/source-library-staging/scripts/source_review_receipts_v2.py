"""Server-only signed inspection receipts for staging PDF page reviews.

Receipts attest that a trusted page-image delivery handler issued an inspection
challenge; they do NOT prove human visual attention. The caller must verify
the image was actually served from the immutable source before issuing one.
Replay prevention requires a database-backed one-time nonce before approvals
may be enabled.
"""
import base64
import hashlib
import hmac
import json
import secrets
import time
from uuid import UUID

TTL_SECONDS = 300

def _b64(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

def _unb64(value):
    if not isinstance(value, str) or len(value) > 4096:
        raise ValueError("Invalid receipt")
    return base64.b64decode(value + "=" * (-len(value) % 4), altchars=b"-_", validate=True)

def _validate(reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page):
    for uid in (reviewer_uid, owner_uid):
        if not isinstance(uid, str) or str(UUID(uid)) != uid:
            raise ValueError("Invalid reviewer or owner")
    if not isinstance(source_sha256, str) or len(source_sha256) != 64 or any(c not in "0123456789abcdef" for c in source_sha256):
        raise ValueError("Invalid source fingerprint")
    if not isinstance(r2_key, str) or not r2_key.startswith(owner_uid + "/"):
        raise ValueError("Invalid owner-scoped key")
    if type(pdf_page) is not int or pdf_page < 1:
        raise ValueError("Invalid PDF page")

def issue_receipt(secret, *, reviewer_uid, owner_uid, source_sha256, r2_key,
                  pdf_page, image_sha256, now=None):
    """Call ONLY after trusted server has served and hashed the original page image."""
    _validate(reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page)
    if not isinstance(image_sha256, str) or len(image_sha256) != 64 or any(c not in "0123456789abcdef" for c in image_sha256):
        raise ValueError("Invalid page-image hash")
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Strong server-only signing key required")
    issued = int(time.time() if now is None else now)
    body = {"v": 1, "reviewer_uid": reviewer_uid, "owner_uid": owner_uid,
            "source_sha256": source_sha256, "r2_key": r2_key, "pdf_page": pdf_page,
            "image_sha256": image_sha256, "iat": issued, "nonce": secrets.token_hex(16)}
    payload = _b64(json.dumps(body, sort_keys=True, separators=(",", ":")).encode())
    signature = _b64(hmac.new(secret, payload.encode(), hashlib.sha256).digest())
    return payload + "." + signature

def verify_receipt(secret, receipt, *, reviewer_uid, owner_uid, source_sha256,
                   r2_key, pdf_page, image_sha256, now=None):
    """Validate signature, binding and expiry. Does not consume nonce."""
    _validate(reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page)
    if not isinstance(secret, bytes) or len(secret) < 32 or not isinstance(receipt, str):
        raise ValueError("Invalid receipt or signing key")
    try:
        payload, signature = receipt.split(".")
        expected = hmac.new(secret, payload.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_unb64(signature), expected):
            raise ValueError("Invalid signature")
        body = json.loads(_unb64(payload))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValueError("Invalid receipt") from exc
    current = int(time.time() if now is None else now)
    expected_fields = {"v": 1, "reviewer_uid": reviewer_uid, "owner_uid": owner_uid,
                       "source_sha256": source_sha256, "r2_key": r2_key,
                       "pdf_page": pdf_page, "image_sha256": image_sha256}
    if not isinstance(body, dict) or any(body.get(k) != v or type(body.get(k)) is not type(v) for k, v in expected_fields.items()):
        raise ValueError("Receipt source/reviewer/page mismatch")
    if type(body.get("iat")) is not int or body["iat"] > current + 30 or current - body["iat"] > TTL_SECONDS:
        raise ValueError("Receipt expired or not yet valid")
    if not isinstance(body.get("nonce"), str) or len(body["nonce"]) != 32:
        raise ValueError("Invalid receipt nonce")
    return body["nonce"]
