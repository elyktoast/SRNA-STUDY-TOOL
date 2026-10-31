"""Server-side staging inspection pipeline with explicit delivery boundary.

This orchestrator is not a public HTTP endpoint. The trusted caller must
authenticate the reviewer, use protected DB roles, and provide server-owned
manifest/R2 adapters. A synchronous image writer must complete without error
before a nonce/receipt can be registered. Successful server-side writes cannot
prove the human actually viewed the page; approvals remain disabled until the
deployed delivery protocol and its acceptance tests are complete.
"""
from source_review_identity_v2 import resolve_admin_reviewer
from source_review_page_loader_v2 import load_verified_review_page
from source_review_receipt_service_v2 import register_delivered_page_receipt


def inspect_and_register_page(*, conn, access_token, auth_provider,
                              protected_role_store, owner_uid, r2_key,
                              pdf_page, manifest_loader, source_loader,
                              write_image, signing_secret, now=None):
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    if reviewer.uid != owner_uid:
        raise ValueError("Reviewer does not own requested source")
    if not callable(write_image):
        raise ValueError("Trusted image delivery writer required")
    page = load_verified_review_page(
        owner_uid=owner_uid, r2_key=r2_key, pdf_page=pdf_page,
        manifest_loader=manifest_loader, source_loader=source_loader)
    # Writer must write these exact trusted PNG bytes; it must not accept a
    # client-provided image digest. A failed write must never mint a receipt.
    write_image(page["png"], content_type="image/png",
                cache_control="private, no-store")
    receipt = register_delivered_page_receipt(
        conn, page=page, access_token=access_token,
        auth_provider=auth_provider,
        protected_role_store=protected_role_store,
        signing_secret=signing_secret,
        delivered_image_sha256=page["image_sha256"], now=now)
    return {"receipt": receipt, "image_sha256": page["image_sha256"],
            "source_sha256": page["source_sha256"],
            "pdf_page": page["pdf_page"]}
