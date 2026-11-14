"""Trusted staging-only page inspection receipt registration.

This service runs after the server has authenticated the reviewer, verified
protected admin membership, fetched and rendered the immutable original PDF,
and successfully delivered the page image. The delivery boundary must invoke
this service only after its delivery confirmation; a browser-supplied hash or
'viewed' boolean is never sufficient evidence.

The nonce and receipt are bound to the same trusted page/source identity.
"""
import time

from source_review_identity_v2 import resolve_admin_reviewer
from source_review_receipts_v2 import issue_receipt, verify_receipt
from source_review_nonces_v2 import register_inspection_nonce, consume_inspection_nonce


def register_delivered_page_receipt(conn, *, page, access_token, auth_provider,
                                    protected_role_store, signing_secret,
                                    delivered_image_sha256, now=None):
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    if not isinstance(page, dict) or page.get("owner_uid") != reviewer.uid:
        raise ValueError("Reviewer does not own delivered page")
    image_sha = page.get("image_sha256")
    if not isinstance(image_sha, str) or delivered_image_sha256 != image_sha:
        raise ValueError("Delivered image does not match trusted rendering")
    issued_at = time.time() if now is None else now
    receipt = issue_receipt(
        signing_secret, reviewer_uid=reviewer.uid, owner_uid=reviewer.uid,
        source_sha256=page["source_sha256"], r2_key=page["r2_key"],
        pdf_page=page["pdf_page"], image_sha256=image_sha, now=issued_at)
    nonce = verify_receipt(
        signing_secret, receipt, reviewer_uid=reviewer.uid,
        owner_uid=reviewer.uid, source_sha256=page["source_sha256"],
        r2_key=page["r2_key"], pdf_page=page["pdf_page"],
        image_sha256=image_sha, now=now)
    # Database registration must succeed before a receipt can be returned.
    with conn.transaction():
        register_inspection_nonce(
            conn, nonce=nonce, reviewer_uid=reviewer.uid,
            owner_uid=reviewer.uid, source_sha256=page["source_sha256"],
            r2_key=page["r2_key"], pdf_page=page["pdf_page"],
            issued_at=issued_at)
    return receipt


def register_acknowledged_page_receipt(conn, *, page, access_token,
                                       auth_provider, protected_role_store,
                                       signing_secret, delivery_challenge,
                                       acknowledged, now=None):
    """Exchange an explicit reviewer acknowledgment for a one-time receipt.

    The caller MUST independently re-render and verify the immutable page from
    trusted storage before calling this function. A client-supplied page/hash
    is not trusted. Acknowledgment is the reviewer's attestation, not objective
    proof of visual attention. No protected approval is written here.
    """
    from source_review_delivery_challenge_v2 import verify_delivery_challenge
    if acknowledged is not True:
        raise ValueError("Explicit inspection acknowledgment required")
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    if not isinstance(page, dict) or page.get("owner_uid") != reviewer.uid:
        raise ValueError("Reviewer does not own inspected page")
    challenge_id = verify_delivery_challenge(
        signing_secret, delivery_challenge, reviewer_uid=reviewer.uid,
        page=page, now=now)
    # Consume the delivery challenge and register the approval receipt in
    # one transaction. A failed receipt registration rolls back consumption.
    with conn.transaction():
        consume_inspection_nonce(
            conn, nonce=challenge_id, reviewer_uid=reviewer.uid,
            owner_uid=reviewer.uid, source_sha256=page["source_sha256"],
            r2_key=page["r2_key"], pdf_page=page["pdf_page"])
        return register_delivered_page_receipt(
            conn, page=page, access_token=access_token,
            auth_provider=auth_provider, protected_role_store=protected_role_store,
            signing_secret=signing_secret,
            delivered_image_sha256=page["image_sha256"], now=now)


def register_delivery_challenge(conn, *, page, access_token, auth_provider,
                                protected_role_store, signing_secret, now=None):
    """Persist a source-bound challenge before returning it with verified PNG."""
    from source_review_delivery_challenge_v2 import (
        issue_delivery_challenge, verify_delivery_challenge)
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    if not isinstance(page, dict) or page.get("owner_uid") != reviewer.uid:
        raise ValueError("Reviewer does not own page")
    issued_at = time.time() if now is None else now
    challenge = issue_delivery_challenge(
        signing_secret, reviewer_uid=reviewer.uid, page=page, now=issued_at)
    challenge_id = verify_delivery_challenge(
        signing_secret, challenge, reviewer_uid=reviewer.uid,
        page=page, now=issued_at)
    with conn.transaction():
        register_inspection_nonce(
            conn, nonce=challenge_id, reviewer_uid=reviewer.uid,
            owner_uid=reviewer.uid, source_sha256=page["source_sha256"],
            r2_key=page["r2_key"], pdf_page=page["pdf_page"],
            issued_at=issued_at)
    return challenge
