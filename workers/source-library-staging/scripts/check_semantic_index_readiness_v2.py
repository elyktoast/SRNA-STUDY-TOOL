"""Staging-only read-only index readiness CLI.

Usage: python check_semantic_index_readiness_v2.py /secure/inventory.json
Requires STAGING_ONLY=true, STAGING_DATABASE_URL, SEMANTIC_INDEX_OWNER_UID,
SEMANTIC_INDEX_EMBEDDING_MODEL. Never generates embeddings or changes DB rows.
"""
import json
import os
import sys

from item_semantic_inventory_reconcile_v2 import load_inventory, reconcile


def check(*, inventory_path, env, connect):
    if env.get("STAGING_ONLY") != "true":
        raise ValueError("Staging-only readiness check")
    owner = env.get("SEMANTIC_INDEX_OWNER_UID")
    model = env.get("SEMANTIC_INDEX_EMBEDDING_MODEL")
    db_url = env.get("STAGING_DATABASE_URL")
    if not all(isinstance(value, str) and value.strip()
               for value in (owner, model, db_url)):
        raise ValueError("Missing staging readiness configuration")
    inventory, digest = load_inventory(inventory_path)
    with connect(db_url, connect_timeout=8, sslmode="require") as conn:
        result = reconcile(conn, owner_uid=owner, embedding_model=model,
                           inventory=inventory)
    # Do not emit item stems, tokens, credentials or individual question IDs.
    return {
        "ready": result["ready"],
        "inventory_digest": digest,
        "expected_count": result["expected_count"],
        "indexed_count": result["indexed_count"],
        "missing_count": result["missing_count"],
        "unexpected_count": result["unexpected_count"],
        "stale_count": result["stale_count"],
    }


def main(argv=None, env=None, connect=None):
    argv = sys.argv[1:] if argv is None else argv
    env = os.environ if env is None else env
    if len(argv) != 1:
        print(json.dumps({"ready": False, "error": "INVALID_ARGUMENTS"}))
        return 2
    try:
        if connect is None:
            import psycopg
            connect = psycopg.connect
        result = check(inventory_path=argv[0], env=env, connect=connect)
    except Exception:
        # Do not leak connection strings or database errors into logs.
        print(json.dumps({"ready": False, "error": "READINESS_UNAVAILABLE"}))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    sys.exit(main())
