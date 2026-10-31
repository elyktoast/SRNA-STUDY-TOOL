"""Authenticated backend-only blind-review result envelope.

HMAC binds the result to item ID and exact screening run. The secret must be
kept in the staging backend, never exposed to browsers or model prompts.
Replay prevention requires server-side single-use run IDs at integration.
"""
import hashlib
import hmac
import json

def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")

def _secret(secret):
    if not isinstance(secret, bytes) or len(secret) < 32:
        raise ValueError("Backend signing key must be at least 32 bytes")

def sign(*, item_id, run_id, result, secret):
    _secret(secret)
    if not isinstance(item_id, str) or not item_id.strip() or not isinstance(run_id, str) or not run_id.strip():
        raise ValueError("Item ID and unique screening run ID required")
    if not isinstance(result, dict):
        raise ValueError("Blind result required")
    body = {"item_id": item_id, "run_id": run_id, "result": result}
    signature = hmac.new(secret, _canonical(body), hashlib.sha256).hexdigest()
    return {**body, "signature": signature}

def verify(envelope, *, item_id, run_id, secret):
    _secret(secret)
    if not isinstance(envelope, dict) or set(envelope) != {"item_id", "run_id", "result", "signature"}:
        raise ValueError("Invalid signed review envelope")
    if not isinstance(item_id, str) or not isinstance(run_id, str) or not item_id or not run_id:
        raise ValueError("Expected item and run IDs required")
    if envelope["item_id"] != item_id or envelope["run_id"] != run_id:
        raise ValueError("Review bound to different item or screening run")
    signature = envelope["signature"]
    if not isinstance(signature, str) or len(signature) != 64:
        raise ValueError("Invalid signature")
    body = {k: envelope[k] for k in ("item_id", "run_id", "result")}
    expected = hmac.new(secret, _canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ValueError("Review signature verification failed")
    if not isinstance(envelope["result"], dict):
        raise ValueError("Invalid review result")
    return envelope["result"]
