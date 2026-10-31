"""Read-only loader for protected staging page-review decisions.

Requires a server-verified reviewer identity and admin authorization supplied
by the trusted server boundary. The SQL table is deliberately NOT created here.
Do not use client-provided JSON or reviewer identifiers as authentication.
"""
from source_review_authorization_v2 import TrustedReviewApproval

SCHEMA = "source_library_staging"

def load_approved_pages(conn, manifest, *, authenticated_reviewer_uid, reviewer_is_admin):
    if reviewer_is_admin is not True or not isinstance(authenticated_reviewer_uid, str) or not authenticated_reviewer_uid:
        raise ValueError("Verified admin reviewer required")
    for key in ("owner_uid", "r2_key", "sha256"):
        if not isinstance(manifest.get(key), str) or not manifest[key]:
            raise ValueError("Missing source identity")
    # Bind all identifiers; never interpolate source or reviewer data into SQL.
    with conn.cursor() as cur:
        cur.execute(
            """select pdf_page from source_library_staging.page_review_approvals_v2
               where owner_uid=%s and source_sha256=%s and r2_key=%s
                 and reviewer_uid=%s and decision='approved'
                 and revoked_at is null
               order by pdf_page for share""",
            (manifest["owner_uid"], manifest["sha256"], manifest["r2_key"],
             authenticated_reviewer_uid))
        pages = [row[0] for row in cur.fetchall()]
    count = manifest.get("pdf_page_count")
    if type(count) is not int or count < 1:
        raise ValueError("Invalid source page count")
    if any(type(page) is not int or page < 1 or page > count for page in pages):
        raise ValueError("Invalid database-approved PDF page")
    if len(pages) != len(set(pages)):
        raise ValueError("Duplicate database page approval")
    return TrustedReviewApproval(
        manifest["owner_uid"], manifest["sha256"], manifest["r2_key"],
        authenticated_reviewer_uid, frozenset(pages))
