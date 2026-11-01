"""Read-only comparison of existing indexed passages with fresh extraction.

No writes, no backfill, no page approval. Source manifests must be independently
verified by the caller against immutable R2 source bytes before this comparison.
"""
from collections import Counter
import hashlib


def passage_fingerprint(content):
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Invalid passage text")
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compare_indexed_passages(conn, *, textbook_id, owner_uid, fresh_passages,
                             expected_page_count, expected_source_sha256):
    from uuid import UUID
    import re
    for name, value in (("textbook_id", textbook_id), ("owner_uid", owner_uid)):
        if not isinstance(value, str):
            raise ValueError("Invalid " + name)
        try:
            if str(UUID(value)) != value.lower():
                raise ValueError()
        except ValueError:
            raise ValueError("Invalid " + name) from None
    if not isinstance(expected_source_sha256, str) or not re.fullmatch(
            r"[a-f0-9]{64}", expected_source_sha256):
        raise ValueError("Verified R2 source digest required")
    if type(expected_page_count) is not int or expected_page_count < 1:
        raise ValueError("Invalid page count")
    if not isinstance(fresh_passages, list) or not fresh_passages:
        raise ValueError("Fresh extraction required")
    if len(fresh_passages) > 300000:
        raise ValueError("Excessive passage count")
    fresh = []
    for i, p in enumerate(fresh_passages):
        if not isinstance(p, dict) or p.get("chunk_index") != i:
            raise ValueError("Invalid fresh passage ordering")
        a, b = p.get("page_start"), p.get("page_end")
        if type(a) is not int or type(b) is not int or not 1 <= a <= b <= expected_page_count:
            raise ValueError("Invalid fresh page range")
        fresh.append((i, a, b, passage_fingerprint(p.get("content"))))
    with conn.cursor() as cur:
        cur.execute(
            """SELECT page_count FROM source_library_staging.textbooks
               WHERE id=%s::uuid AND owner_uid=%s::uuid AND status='ready'""",
            (textbook_id, owner_uid))
        row = cur.fetchone()
        if not row or row[0] != expected_page_count:
            raise ValueError("Indexed textbook identity or page count mismatch")
        cur.execute(
            """SELECT p.chunk_index,p.page_start,p.page_end,p.content
               FROM source_library_staging.passages p
               WHERE p.textbook_id=%s::uuid ORDER BY p.chunk_index""",
            (textbook_id,))
        indexed_rows = cur.fetchall()
    indexed = [(i, a, b, passage_fingerprint(content))
               for i, a, b, content in indexed_rows]
    exact = indexed == fresh
    return {
        "indexed_passage_count": len(indexed),
        "fresh_passage_count": len(fresh),
        "same_ordered_passages_and_pages": exact,
        "indexed_only_fingerprints": sum((Counter(indexed) - Counter(fresh)).values()),
        "fresh_only_fingerprints": sum((Counter(fresh) - Counter(indexed)).values()),
        "source_sha256": expected_source_sha256,
        "provenance_backfilled": False,
        "approved_for_citation": False,
    }
