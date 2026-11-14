"""Trusted staging-only adapter from validated request bytes to approval service.

This module is not an HTTP route. A server must authenticate the reviewer,
load the source from trusted storage, verify the rendered page digest, and
verify a one-time receipt before any approval write.
"""
from source_review_decision_request_v2 import parse_approval_request
from source_review_page_loader_v2 import load_verified_review_page
from source_review_r2_loader_v2 import fetch_verified_staging_pdf
from source_review_identity_v2 import resolve_admin_reviewer
from source_review_approval_service_v2 import approve_inspected_page


def approve_verified_request(runtime, *, access_token, body):
    request = parse_approval_request(body)
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=runtime.auth,
        protected_role_store=runtime.roles)
    manifest = runtime.manifest(token=access_token, r2_key=request["path"])
    if manifest.get("owner_uid") != reviewer.uid or manifest.get("r2_key") != request["path"]:
        raise ValueError("Reviewer does not own source")
    if manifest.get("sha256") != request["source_sha256"]:
        raise ValueError("Source fingerprint mismatch")
    page_number = request["page"]
    if type(manifest.get("pdf_page_count")) is not int or not 1 <= page_number <= manifest["pdf_page_count"]:
        raise ValueError("Physical PDF page outside trusted manifest")
    page = load_verified_review_page(
        owner_uid=reviewer.uid, r2_key=request["path"], pdf_page=page_number,
        manifest_loader=lambda owner, key: manifest,
        source_loader=lambda owner, key: fetch_verified_staging_pdf(
            runtime.r2, owner_uid=owner, r2_key=key,
            expected_sha256=manifest["sha256"]))
    if (page.get("owner_uid") != reviewer.uid
            or page.get("r2_key") != request["path"]
            or page.get("source_sha256") != manifest["sha256"]
            or type(page.get("pdf_page")) is not int
            or page["pdf_page"] != page_number):
        raise ValueError("Verified page identity mismatch")
    if page.get("image_sha256") != request["image_sha256"]:
        raise ValueError("Rendered image fingerprint mismatch")
    # The classification is explicitly preserved in the auditable note while
    # the existing protected approval schema continues using decision=approved.
    note = "[" + request["classification"] + "] " + request["review_note"].strip()
    return approve_inspected_page(
        runtime.conn, manifest, pdf_page=page_number, review_note=note,
        receipt=request["receipt"], image_sha256=page["image_sha256"],
        receipt_secret=runtime.secret, access_token=access_token,
        auth_provider=runtime.auth, protected_role_store=runtime.roles)
