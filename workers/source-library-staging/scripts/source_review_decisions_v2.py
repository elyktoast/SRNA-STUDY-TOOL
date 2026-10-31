"""Protected staging page-review decision writer (server-only, no HTTP route).

The caller must supply a verified reviewer identity and evidence that the
original PDF page image was inspected. Database privileges are independent
of human reviewer authorization. Requires the approved staging migration.
"""
from source_review_identity_v2 import resolve_admin_reviewer


def record_page_decision(conn, manifest, *, pdf_page, decision, review_note,
                         page_image_inspected, access_token,
                         auth_provider, protected_role_store):
    reviewer = resolve_admin_reviewer(
        access_token, auth_provider=auth_provider,
        protected_role_store=protected_role_store)
    if not isinstance(manifest, dict) or manifest.get("owner_uid") != reviewer.uid:
        raise ValueError("Reviewer does not own source")
    if page_image_inspected is not True:
        raise ValueError("Original PDF page-image inspection required")
    if type(pdf_page) is not int or pdf_page < 1 or pdf_page > manifest.get("pdf_page_count", 0):
        raise ValueError("Invalid physical PDF page")
    if decision not in ("approved", "rejected", "revoked"):
        raise ValueError("Invalid review decision")
    if not isinstance(review_note, str) or not review_note.strip():
        raise ValueError("Review justification required")
    if not isinstance(manifest.get("sha256"), str) or len(manifest["sha256"]) != 64:
        raise ValueError("Source fingerprint required")
    if not isinstance(manifest.get("r2_key"), str) or not manifest["r2_key"].startswith(reviewer.uid + "/"):
        raise ValueError("Owner-scoped source key required")
    if decision == "revoked":
        sql = """UPDATE source_library_staging.page_review_approvals_v2
                 SET revoked_at=now(), review_note=%s
                 WHERE owner_uid=%s AND source_sha256=%s AND r2_key=%s
                   AND pdf_page=%s AND reviewer_uid=%s
                   AND revoked_at IS NULL"""
        args = (review_note, reviewer.uid, manifest["sha256"],
                manifest["r2_key"], pdf_page, reviewer.uid)
    else:
        sql = """INSERT INTO source_library_staging.page_review_approvals_v2
                 (owner_uid, source_sha256, r2_key, pdf_page,
                  reviewer_uid, decision, review_note, revoked_at)
                 VALUES (%s,%s,%s,%s,%s,%s,%s,NULL)
                 ON CONFLICT (owner_uid,source_sha256,r2_key,pdf_page,reviewer_uid)
                 DO UPDATE SET decision=excluded.decision,
                   review_note=excluded.review_note, reviewed_at=now(),
                   revoked_at=NULL"""
        args = (reviewer.uid, manifest["sha256"], manifest["r2_key"],
                pdf_page, reviewer.uid, decision, review_note)
    with conn.cursor() as cur:
        cur.execute(sql, args)
        affected = cur.rowcount
    return affected
