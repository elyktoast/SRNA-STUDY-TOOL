"""Postgres/Supabase staging single-use blind-review registry.

Run migrations privately with a trusted staging DB connection. No client-side
access, service-role exposure, model calls, or automatic schema changes.
"""
from item_blind_attestation_v2 import verify
from item_screening_blind_handoff_v2 import attach

SCHEMA = "source_library_staging"

def register(conn, *, run_id, item_id, owner_uid):
    if not all(isinstance(v, str) and v.strip() for v in (run_id, item_id, owner_uid)):
        raise ValueError("Run, item, and owner required")
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO source_library_staging.blind_review_runs "
            "(run_id,item_id,owner_uid,state) VALUES (%s,%s,%s,'pending')",
            (run_id, item_id, owner_uid))
    conn.commit()

def consume(conn, screening, envelope, *, item_id, run_id, owner_uid, secret):
    if not all(isinstance(v, str) and v.strip() for v in (item_id, run_id, owner_uid)):
        raise ValueError("Run, item, and owner required")
    blind = verify(envelope, item_id=item_id, run_id=run_id, secret=secret)
    updated = attach(screening, blind)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE source_library_staging.blind_review_runs "
                "SET state='consumed', consumed_at=now(), blind_status=%s "
                "WHERE run_id=%s AND item_id=%s AND owner_uid=%s AND state='pending' "
                "RETURNING run_id",
                (blind["status"], run_id, item_id, owner_uid))
            if cur.fetchone() is None:
                raise ValueError("Unknown, mismatched, or already consumed review run")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return updated
