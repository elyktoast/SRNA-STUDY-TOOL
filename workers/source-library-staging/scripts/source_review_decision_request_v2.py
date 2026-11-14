"""Strict, transport-independent parser for staging review decision requests.

Parsing is NOT authorization and never issues receipts or writes approvals.
Only the trusted approval service can verify a one-time inspection receipt.
"""
import json
import re

MAX_BODY_BYTES = 8192
ALLOWED_CLASSIFICATIONS = frozenset(("non_content_divider", "content_reviewed"))


def _unique_fields(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate approval request field")
        result[key] = value
    return result


def _reject_nonfinite(value):
    raise ValueError("Non-finite approval request number")


def parse_approval_request(body):
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY_BYTES:
        raise ValueError("Invalid approval request size")
    try:
        value = json.loads(body.decode("utf-8", errors="strict"),\n                           object_pairs_hook=_unique_fields,\n                           parse_constant=_reject_nonfinite)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid approval request JSON") from exc
    if not isinstance(value, dict) or set(value) != {
            "path", "page", "source_sha256", "image_sha256",
            "receipt", "classification", "review_note"}:
        raise ValueError("Invalid approval request fields")
    path = value["path"]
    page = value["page"]
    if (not isinstance(path, str) or len(path) > 1024
            or not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}/[^\\\x00-\x1f\x7f]+\.pdf", path)
            or any(part in ("", ".", "..") for part in path.split("/"))):
        raise ValueError("Invalid approval source key")
    if type(page) is not int or not 1 <= page <= 100000:
        raise ValueError("Invalid physical PDF page")
    for key in ("source_sha256", "image_sha256"):
        if not isinstance(value[key], str) or re.fullmatch(r"[0-9a-f]{64}", value[key]) is None:
            raise ValueError("Invalid source or image fingerprint")
    if not isinstance(value["receipt"], str) or not 1 <= len(value["receipt"]) <= 4096:
        raise ValueError("Invalid inspection receipt")
    if not isinstance(value["classification"], str) or value["classification"] not in ALLOWED_CLASSIFICATIONS:
        raise ValueError("Invalid review classification")
    note = value["review_note"]
    if (not isinstance(note, str) or not 8 <= len(note.strip()) <= 1000
            or any(ord(char) < 32 or ord(char) == 127 for char in note)):
        raise ValueError("Review justification required")
    return value
