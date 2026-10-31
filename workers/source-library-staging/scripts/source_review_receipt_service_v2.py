"""Trusted staging-only page inspection receipt registration.

This service runs after the server has authenticated the reviewer, verified
protected admin membership, fetched and rendered the immutable original PDF,
and successfully delivered the page image. The delivery boundary must invoke
this service only after its delivery confirmation; a browser-supplied hash or
'viewed' boolean is never sufficient evidence.

The nonce and receipt are bound to the same trusted page/source identity.
"""
from source_review_identity_v2 import resolve_admin_reviewer
from source_review_receipts_v2 import issue_receipt, verify_receipt
from source_review_nonces_v2 import register_inspection_nonce


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
    receipt = issue_receipt(
        signing_secret, reviewer_uid=reviewer.uid, owner_uid=reviewer.uid,
        source_sha256=page["source_sha256"], r2_key=page["r2_key"],
        pdf_page=page["pdf_page"], image_sha256=image_sha, now=now)
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
            issued_at=now if now is not None else __import__("time").time())
    return receipt
