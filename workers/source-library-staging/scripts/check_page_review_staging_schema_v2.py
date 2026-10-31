"""Read-only preflight for staging textbook page approvals; no DDL or writes."""
TABLE = "source_library_staging.page_review_approvals_v2"
REQUIRED = {
    "id": "uuid", "owner_uid": "uuid", "source_sha256": "text",
    "r2_key": "text", "pdf_page": "integer", "reviewer_uid": "uuid",
    "decision": "text", "reviewed_at": "timestamp with time zone",
    "revoked_at": "timestamp with time zone", "review_note": "text",
}

def preflight(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user")
        db_name, _db_user = cur.fetchone()
        cur.execute("SELECT to_regclass(%s)", (TABLE,))
        row = cur.fetchone()
        if not row or row[0] is None:
            return {"ready": False, "database": db_name, "reason": "migration_not_applied"}
        cur.execute(
            "SELECT column_name,data_type FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s",
            ("source_library_staging", "page_review_approvals_v2"))
        columns = dict(cur.fetchall())
        cur.execute(
            "SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(%s)", (TABLE,))
        rls_row = cur.fetchone()
        cur.execute(
            "SELECT has_table_privilege('anon',%s,'SELECT'),"
            "has_table_privilege('authenticated',%s,'SELECT'),"
            "has_table_privilege('anon',%s,'INSERT'),"
            "has_table_privilege('authenticated',%s,'INSERT'),"
            "has_table_privilege('anon',%s,'UPDATE'),"
            "has_table_privilege('authenticated',%s,'UPDATE'),"
            "has_table_privilege('anon',%s,'DELETE'),"
            "has_table_privilege('authenticated',%s,'DELETE')",
            (TABLE,) * 8)
        grants = cur.fetchone()
        cur.execute(
            "SELECT has_schema_privilege('anon',%s,'CREATE'),"
            "has_schema_privilege('authenticated',%s,'CREATE')",
            ("source_library_staging", "source_library_staging"))
        schema_create_grants = cur.fetchone()
    issues = ["column_mismatch:" + name for name, kind in REQUIRED.items()
              if columns.get(name) != kind]
    if not rls_row or rls_row[0] is not True:
        issues.append("rls_not_enabled")
    if not grants or any(value is not False for value in grants):
        issues.append("client_table_privilege_present")
    if not schema_create_grants or any(value is not False for value in schema_create_grants):
        issues.append("client_schema_create_privilege_present")
    return {"ready": not issues, "database": db_name,
            "reason": "ok" if not issues else "schema_or_permission_mismatch",
            "issues": issues}
