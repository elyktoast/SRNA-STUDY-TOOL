"""Trusted reviewer authorization boundary for staging extraction approvals.

The caller MUST obtain reviewer identity and authorization from a verified
server-side session and protected role store, never user JSON or JWT user_metadata.
This module only validates that explicit trusted inputs match the source.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class TrustedReviewApproval:
    owner_uid: str
    source_sha256: str
    r2_key: str
    reviewer_uid: str
    approved_pages: frozenset[int]

def approved_pages_for_import(manifest, approval, *, authenticated_reviewer_uid, reviewer_is_admin):
    if not isinstance(approval, TrustedReviewApproval):
        raise ValueError("Trusted server-side review approval required")
    if not isinstance(authenticated_reviewer_uid, str) or not authenticated_reviewer_uid:
        raise ValueError("Authenticated reviewer required")
    if reviewer_is_admin is not True:
        raise ValueError("Authorized admin reviewer required")
    if approval.reviewer_uid != authenticated_reviewer_uid:
        raise ValueError("Review approval reviewer mismatch")
    for key in ("owner_uid", "source_sha256", "r2_key"):
        manifest_key = "sha256" if key == "source_sha256" else key
        if getattr(approval, key) != manifest.get(manifest_key):
            raise ValueError("Review approval source mismatch")
    count = manifest.get("pdf_page_count")
    if type(count) is not int or count < 1 or not isinstance(approval.approved_pages, frozenset):
        raise ValueError("Invalid approval page metadata")
    if any(type(p) is not int or not 1 <= p <= count for p in approval.approved_pages):
        raise ValueError("Invalid approved PDF page")
    return approval.approved_pages
