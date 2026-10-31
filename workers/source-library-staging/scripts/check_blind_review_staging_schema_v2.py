"""Read-only preflight for the private staging blind-review schema.

Run with a restricted staging connection. No migrations or writes performed.
"""
from uuid import UUID

TABLE = "source_library_staging.blind_review_runs"
REQUIRED = {
    "run_id": "text", "item_id": "text", "owner_uid": "uuid",
    "state": "text", "blind_status": "text",
    "created_at": "timestamp with time zone",
    "consumed_at": "timestamp with time zone",
}

def preflight(conn, *, expected_project_id=None):
    if expected_project_id is not None:
        if not isinstance(expected_project_id, str) or not expected_project_id.strip():
            raise ValueError("Expected project ID required")
    with conn.cursor() as cur:
        cur.execute("SELECT current_database(), current_user")
        db_name, db_user = cur.fetchone()
        cur.execute("SELECT to_regclass(%s)", (TABLE,))
        row = cur.fetchone()
        if not row or row[0] is None:
            return {"ready": False, "database": db_name, "reason": "migration_not_applied"}
        cur.execute(
            "SELECT column_name,data_type FROM information_schema.columns "
            "WHERE table_schema=%s AND table_name=%s",
            ("source_library_staging", "blind_review_runs"))
        columns = dict(cur.fetchall())
        cur.execute(
            "SELECT relrowsecurity FROM pg_class WHERE oid=to_regclass(%s)", (TABLE,))
        rls_row = cur.fetchone()
        cur.execute(
            "SELECT has_table_privilege('anon',%s,'SELECT'),"
            "has_table_privilege('authenticated',%s,'SELECT'),"
            "has_table_privilege('anon',%s,'INSERT'),"
            "has_table_privilege('authenticated',%s,'INSERT')",
            (TABLE, TABLE, TABLE, TABLE))
        grants = cur.fetchone()
    errors = []
    for name, kind in REQUIRED.items():
        if columns.get(name) != kind:
            errors.append("column_mismatch:" + name)
    if not rls_row or rls_row[0] is not True:
        errors.append("rls_not_enabled")
    if any(grants):
        errors.append("client_table_privilege_present")
    return {"ready": not errors, "database": db_name,
            "reason": "ok" if not errors else "schema_or_permission_mismatch",
            "issues": errors}
