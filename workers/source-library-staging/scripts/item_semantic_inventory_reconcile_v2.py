"""Read-only, fail-closed comparison of canonical inventory to staging embeddings.

No provider calls, mutations, or approval/publishing side effects.
"""
from array import array
import json
import hashlib
import math
import os
import re
from pathlib import Path
from uuid import UUID

HASH = re.compile(r"^[a-f0-9]{64}$")
PAGE_SIZE = 1000
MAX_ITEMS = 10000
_inventory_cache = None


def _file_version(source):
    stat = os.fstat(source.fileno())
    return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)


def load_inventory(path):
    global _inventory_cache
    with Path(path).open(encoding="utf-8") as source:
        key = _file_version(source)
        cached = _inventory_cache
        if cached is None or cached[0] != key:
            entries = _validate_inventory(json.load(source))
            cached = (key, entries)
        if key != _file_version(source):
            raise ValueError("Canonical inventory changed during verification")
        _inventory_cache = cached
    inventory, digest = cached[1]
    return dict(inventory), digest


def _validate_inventory(data):

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
    # Preserve exporter order: JavaScript localeCompare and Python Unicode sorting
    # can differ, so re-sorting here could reject an otherwise valid export.
    canonical = [{"item_id": entry["item_id"], "stem_hash": entry["stem_hash"]}
                 for entry in entries]
    calculated = hashlib.sha256(
        json.dumps(canonical, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    if calculated != digest:
        raise ValueError("Canonical inventory digest mismatch")
    return inventory, digest


def _scan_index(conn, *, owner_uid, embedding_model, inventory, retain_vectors=False):
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
    vectors = {}
    dimensions = None
    last_id = ""
    # psycopg's binary array decoder avoids converting millions of printed
    # float literals while preserving the PostgreSQL double values exactly.
    try:
        from psycopg import Connection
        binary = isinstance(conn, Connection)
    except ImportError:
        binary = False
    cursor = conn.cursor(binary=True) if binary else conn.cursor()
    with cursor as cur:
        while True:
            cur.execute(
                """select item_id, stem_hash, embedding from source_library_staging.question_semantic_index_v2
                   where owner_uid=%s and embedding_model=%s and item_id COLLATE "C">%s
                   order by item_id COLLATE "C" limit %s""",
                (owner, embedding_model, last_id, PAGE_SIZE))
            page = cur.fetchall()
            if len(page) > PAGE_SIZE or any(
                not isinstance(row[0], str) or row[0] <= last_id
                or (i > 0 and row[0] <= page[i - 1][0])
                for i, row in enumerate(page)
            ):
                raise ValueError("Invalid semantic index pagination")
            for item_id, stem_hash, embedding in page:
                if item_id in observed:
                    raise ValueError("Duplicate semantic index item")
                if (not isinstance(embedding, (list, tuple))
                        or not 2 <= len(embedding) <= 4096):
                    raise ValueError("Invalid indexed embedding")
                if embedding_model == '@cf/baai/bge-m3' and len(embedding) != 1024:
                    raise ValueError('Invalid Cloudflare embedding dimensions')
                # Bound magnitude before cosine: finite float components can
                # still overflow during squaring and yield a false similarity.
                if any(type(v) not in (int, float) or not math.isfinite(v)
                       or abs(v) > 1e100 for v in embedding):
                    raise ValueError("Invalid indexed embedding")
                # A row only needs a usable norm here. Calculating cosine
                # against itself would scan the same components three times.
                squared_norm = sum(value * value for value in embedding)
                if not math.isfinite(squared_norm) or squared_norm <= 0:
                    raise ValueError("Invalid indexed embedding")
                if dimensions is None:
                    dimensions = len(embedding)
                elif len(embedding) != dimensions:
                    raise ValueError("Inconsistent indexed embedding dimensions")
                observed[item_id] = stem_hash
                if retain_vectors:
                    vectors[item_id] = array("d", embedding)
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
    report = {
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
    return report, vectors


def reconcile(conn, *, owner_uid, embedding_model, inventory):
    report, _ = _scan_index(conn, owner_uid=owner_uid, embedding_model=embedding_model,
                            inventory=inventory)
    return report


def reconciled_vectors(conn, *, owner_uid, embedding_model, inventory):
    """Return all validated embeddings from a complete scan, or no snapshot."""
    report, vectors = _scan_index(conn, owner_uid=owner_uid, embedding_model=embedding_model,
                                  inventory=inventory, retain_vectors=True)
    return vectors if report["ready"] else None
