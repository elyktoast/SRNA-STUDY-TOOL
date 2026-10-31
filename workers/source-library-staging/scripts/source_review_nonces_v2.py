"""Atomic server-side one-time receipt registration and consumption.

Requires a privileged direct PostgreSQL connection. Issuance must occur only
after authenticated delivery of the original page image and independent
verification of its SHA-256 digest. The schema is a draft until approved.
"""
import hashlib
import re
from uuid import UUID
from datetime import datetime, timedelta, timezone
from source_review_receipts_v2 import TTL_SECONDS


def _validate_nonce_binding(nonce, reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page):
    if not isinstance(nonce, str) or re.fullmatch(r"[0-9a-f]{32}", nonce) is None:
        raise ValueError("Invalid inspection nonce")
    for uid in (reviewer_uid, owner_uid):
        if not isinstance(uid, str):
            raise ValueError("Invalid reviewer or owner")
        try:
            if str(UUID(uid)) != uid:
                raise ValueError("Invalid reviewer or owner")
        except (ValueError, AttributeError) as exc:
            raise ValueError("Invalid reviewer or owner") from exc
    if not isinstance(source_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
        raise ValueError("Invalid source fingerprint")
    if not isinstance(r2_key, str) or not r2_key.startswith(owner_uid + "/"):
        raise ValueError("Invalid owner-scoped source key")
    if type(pdf_page) is not int or pdf_page < 1:
        raise ValueError("Invalid physical PDF page")


def register_inspection_nonce(conn, *, nonce, reviewer_uid, owner_uid,
                              source_sha256, r2_key, pdf_page, issued_at):
    _validate_nonce_binding(nonce, reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page)
    digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    expiry = datetime.fromtimestamp(issued_at, tz=timezone.utc) + timedelta(seconds=TTL_SECONDS)
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO source_library_staging.page_inspection_nonces_v2
               (nonce_sha256,reviewer_uid,owner_uid,source_sha256,r2_key,pdf_page,expires_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (digest, reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page, expiry))
        if cur.rowcount != 1:
            raise ValueError("Receipt registration failed")
    return digest


def consume_inspection_nonce(conn, *, nonce, reviewer_uid, owner_uid,
                             source_sha256, r2_key, pdf_page):
    digest = hashlib.sha256(nonce.encode("ascii")).hexdigest()
    with conn.cursor() as cur:
        cur.execute(
            """UPDATE source_library_staging.page_inspection_nonces_v2
               SET consumed_at=now()
               WHERE nonce_sha256=%s AND reviewer_uid=%s AND owner_uid=%s
                 AND source_sha256=%s AND r2_key=%s AND pdf_page=%s
                 AND consumed_at IS NULL AND expires_at > now()""",
            (digest, reviewer_uid, owner_uid, source_sha256, r2_key, pdf_page))
        if cur.rowcount != 1:
            raise ValueError("Receipt missing, expired, or already consumed")
    return True
