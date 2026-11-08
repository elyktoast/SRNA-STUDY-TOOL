"""Staging-only offline embedding import. Never contacts embedding providers.

Input is a JSON file with model, inventory_digest and entries containing
item_id, stem_hash and embedding. Default mode validates without DB writes.
"""
import argparse
import json
import math
import os
import sys
from pathlib import Path
from uuid import UUID
from item_semantic_inventory_reconcile_v2 import load_inventory, reconcile

MAX_ITEMS = 10000
MAX_BYTES = 200_000_000
BATCH_SIZE = 100


def prepare(inventory_path, vectors_path, *, model):
    inventory, digest = load_inventory(inventory_path)
    path = Path(vectors_path)
    if path.stat().st_size > MAX_BYTES:
        raise ValueError("Embedding bundle too large")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(bundle, dict) or set(bundle) !=
            {"schema_version", "inventory_digest", "embedding_model", "entries"}
            or type(bundle["schema_version"]) is not int or bundle["schema_version"] != 1
            or bundle["inventory_digest"] != digest
            or bundle["embedding_model"] != model
            or not isinstance(bundle["entries"], list)
            or len(bundle["entries"]) != len(inventory)):
        raise ValueError("Embedding bundle metadata mismatch")
    rows, seen, dimension = [], set(), None
    for entry in bundle["entries"]:
        if not isinstance(entry, dict) or set(entry) != {"item_id", "stem_hash", "embedding"}:
            raise ValueError("Invalid embedding entry")
        item_id, stem_hash, vector = entry["item_id"], entry["stem_hash"], entry["embedding"]
        if (not isinstance(item_id, str) or item_id not in inventory
                or item_id in seen or inventory[item_id] != stem_hash):
            raise ValueError("Embedding inventory mismatch")
        if (not isinstance(vector, list) or not 2 <= len(vector) <= 4096
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       or abs(v) > 1e100 for v in vector)
                or not any(v != 0 for v in vector)):
            raise ValueError("Invalid embedding vector")
        if dimension is None:
            dimension = len(vector)
        elif dimension != len(vector):
            raise ValueError("Mixed embedding dimensions")
        seen.add(item_id)
        rows.append((item_id, stem_hash, vector))
    if seen != set(inventory):
        raise ValueError("Incomplete embedding inventory")
    rows.sort(key=lambda row: row[0])
    return rows, inventory, digest, dimension


def apply(conn, *, owner_uid, model, rows, inventory):
    owner = str(UUID(owner_uid))
    # Single transaction; any conflicting owner or failed verification rolls back.
    with conn.transaction():
        with conn.cursor() as cur:
            for start in range(0, len(rows), BATCH_SIZE):
                for item_id, stem_hash, vector in rows[start:start + BATCH_SIZE]:
                    cur.execute(
                        """insert into source_library_staging.question_semantic_index_v2
                           (item_id, owner_uid, embedding_model, stem_hash, embedding)
                           values (%s,%s,%s,%s,%s)
                           on conflict (item_id) do update
                           set stem_hash=excluded.stem_hash,
                               embedding=excluded.embedding,
                               updated_at=now()
                           where question_semantic_index_v2.owner_uid=excluded.owner_uid
                             and question_semantic_index_v2.embedding_model=excluded.embedding_model""",
                        (item_id, owner, model, stem_hash, vector))
                    if cur.rowcount != 1:
                        raise ValueError("Conflicting index ownership or model")
        result = reconcile(conn, owner_uid=owner, embedding_model=model, inventory=inventory)
        if not result["ready"]:
            raise ValueError("Imported index failed reconciliation")
    return result


def main(argv=None, env=None, connect=None):
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser(description="Staging-only offline embedding import")
    parser.add_argument("inventory")
    parser.add_argument("vectors")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    try:
        if env.get("STAGING_ONLY") != "true":
            raise ValueError("Staging-only operation")
        model = env.get("SEMANTIC_INDEX_EMBEDDING_MODEL")
        owner = env.get("SEMANTIC_INDEX_OWNER_UID")
        if not isinstance(model, str) or not model.strip():
            raise ValueError("Missing embedding model")
        rows, inventory, digest, dimensions = prepare(args.inventory, args.vectors, model=model)
        if args.apply:
            if env.get("SEMANTIC_INDEX_IMPORT_OPT_IN") != "true":
                raise ValueError("Index import not authorized")
            if not owner or not env.get("STAGING_DATABASE_URL"):
                raise ValueError("Missing staging database configuration")
            if connect is None:
                import psycopg
                connect = psycopg.connect
            with connect(env["STAGING_DATABASE_URL"], connect_timeout=8, sslmode="require") as conn:
                apply(conn, owner_uid=owner, model=model, rows=rows, inventory=inventory)
        print(json.dumps({"ok": True, "applied": args.apply, "count": len(rows),
                          "dimensions": dimensions, "inventory_digest": digest}))
        return 0
    except Exception:
        print(json.dumps({"ok": False, "error": "IMPORT_UNAVAILABLE"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
