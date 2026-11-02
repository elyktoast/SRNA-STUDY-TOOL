"""Trusted staging approval orchestration; never expose to an untrusted client.

The caller MUST load the immutable manifest and page-image digest from trusted
storage, and MUST issue receipts only after serving the original PDF page.
Both nonce consumption and decision write run on the same DB transaction.
"""
from source_review_receipts_v2 import verify_receipt
from source_review_nonces_v2 import consume_inspection_nonce
from source_review_decisions_v2 import record_page_decision


def approve_inspected_page(conn, manifest, *, pdf_page, review_note, receipt,
                           image_sha256, receipt_secret, access_token,
                           auth_provider, protected_role_store, now=None):
    if not isinstance(manifest, dict):
        raise ValueError("Trusted source manifest required")
    # Resolve identity before touching the receipt; the decision writer repeats
    # authorization inside the transaction as defense in depth.
    from source_review_identity_v2 import resolve_admin_reviewer
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    if manifest.get("owner_uid") != reviewer.uid:
        raise ValueError("Reviewer does not own source")
    nonce = verify_receipt(
        receipt_secret, receipt, reviewer_uid=reviewer.uid,
        owner_uid=reviewer.uid, source_sha256=manifest["sha256"],
        r2_key=manifest["r2_key"], pdf_page=pdf_page,
        image_sha256=image_sha256, now=now)
    # Both operations must commit or roll back together. A real DB connection
    # must support transaction context management (e.g. psycopg Connection).
    # Never call this from a browser route with caller-supplied manifest/hash.
    with conn.transaction():
        consume_inspection_nonce(
            conn, nonce=nonce, reviewer_uid=reviewer.uid,
            owner_uid=reviewer.uid, source_sha256=manifest["sha256"],
            r2_key=manifest["r2_key"], pdf_page=pdf_page)
        return record_page_decision(
            conn, manifest, pdf_page=pdf_page, decision="approved",
            review_note=review_note, page_image_inspected=True,
            access_token=access_token, auth_provider=auth_provider,
            protected_role_store=protected_role_store,
            _verified_inspection=True)
