"""Read-only, fail-closed comparison of canonical inventory to staging embeddings.

No provider calls, mutations, or approval/publishing side effects.
"""
import json
import re
from pathlib import Path
from uuid import UUID

HASH = re.compile(r"^[a-f0-9]{64}$")
PAGE_SIZE = 1000
MAX_ITEMS = 10000


def load_inventory(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("Unsupported canonical inventory schema")
    entries = data.get("entries")
    count = data.get("item_count")
    digest = data.get("inventory_digest")
    if (not isinstance(entries, list) or not entries or len(entries) > MAX_ITEMS
            or type(count) is not int or count != len(entries)
            or not isinstance(digest, str) or not HASH.fullmatch(digest)):
        raise ValueError("Invalid canonical inventory metadata")
    inventory = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Invalid canonical inventory entry")
        item_id, stem_hash = entry.get("item_id"), entry.get("stem_hash")
        if (not isinstance(item_id, str) or not item_id or len(item_id) > 128
                or not isinstance(stem_hash, str) or not HASH.fullmatch(stem_hash)
                or item_id in inventory):
            raise ValueError("Invalid or duplicate canonical item")
        inventory[item_id] = stem_hash
    return inventory, digest


def reconcile(conn, *, owner_uid, embedding_model, inventory):
    owner = str(UUID(owner_uid))
    if (not isinstance(embedding_model, str) or not embedding_model.strip()
            or not isinstance(inventory, dict) or not inventory
            or len(inventory) > MAX_ITEMS):
        raise ValueError("Invalid reconciliation configuration")
    if any(not isinstance(key, str) or not key or len(key) > 128
           or not isinstance(value, str) or not HASH.fullmatch(value)
           for key, value in inventory.items()):
        raise ValueError("Invalid canonical inventory")
    observed = {}
    last_id = ""
    with conn.cursor() as cur:
        while True:
            cur.execute(
                """select item_id, stem_hash from source_library_staging.question_semantic_index_v2
                   where owner_uid=%s and embedding_model=%s and item_id>%s
                   order by item_id limit %s""",
                (owner, embedding_model, last_id, PAGE_SIZE))
            page = cur.fetchall()
            if len(page) > PAGE_SIZE or any(
                not isinstance(row[0], str) or row[0] <= last_id
                or (i > 0 and row[0] <= page[i - 1][0])
                for i, row in enumerate(page)
            ):
                raise ValueError("Invalid semantic index pagination")
            for item_id, stem_hash in page:
                if item_id in observed:
                    raise ValueError("Duplicate semantic index item")
                observed[item_id] = stem_hash
            if len(observed) > MAX_ITEMS:
                raise ValueError("Semantic index exceeds inventory cap")
            if len(page) < PAGE_SIZE:
                break
            last_id = page[-1][0]
    expected_ids, actual_ids = set(inventory), set(observed)
    missing = sorted(expected_ids - actual_ids)
    unexpected = sorted(actual_ids - expected_ids)
    stale = sorted(item_id for item_id in expected_ids & actual_ids
                   if inventory[item_id] != observed[item_id])
    return {
        "ready": not (missing or unexpected or stale),
        "expected_count": len(expected_ids),
        "indexed_count": len(actual_ids),
        "missing_count": len(missing),
        "unexpected_count": len(unexpected),
        "stale_count": len(stale),
        "missing_ids": missing,
        "unexpected_ids": unexpected,
        "stale_ids": stale,
    }
