"""Staging-only SQLite single-use blind-review handoff.

Database must be a private persistent staging path, not :memory: in deployment.
A production integration must authenticate the invoking service and manage
the signing key outside this module.
"""
import json
import sqlite3
from item_blind_attestation_v2 import verify
from item_screening_blind_handoff_v2 import attach

def initialize(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS blind_review_runs (
        run_id TEXT PRIMARY KEY,
        item_id TEXT NOT NULL,
        state TEXT NOT NULL CHECK (state IN ('pending','consumed')),
        consumed_result TEXT
    )""")
    conn.commit()

def register(conn, *, run_id, item_id):
    if not run_id or not item_id or not isinstance(run_id, str) or not isinstance(item_id, str):
        raise ValueError("Unique run and item IDs required")
    conn.execute("INSERT INTO blind_review_runs (run_id,item_id,state) VALUES (?,?, 'pending')",
                 (run_id, item_id))
    conn.commit()

def consume(conn, screening, envelope, *, item_id, run_id, secret):
    # Validate signature and content before attempting the single-use claim.
    blind = verify(envelope, item_id=item_id, run_id=run_id, secret=secret)
    updated = attach(screening, blind)
    # IMMEDIATE serializes competing claims across SQLite connections.
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute("SELECT item_id,state FROM blind_review_runs WHERE run_id=?",
                           (run_id,)).fetchone()
        if row is None or row[0] != item_id or row[1] != "pending":
            raise ValueError("Unknown, mismatched, or already consumed review run")
        changed = conn.execute(
            "UPDATE blind_review_runs SET state='consumed',consumed_result=? "
            "WHERE run_id=? AND item_id=? AND state='pending'",
            (json.dumps({"blind_status": blind["status"]}), run_id, item_id)).rowcount
        if changed != 1:
            raise ValueError("Review run already claimed")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    return updated
