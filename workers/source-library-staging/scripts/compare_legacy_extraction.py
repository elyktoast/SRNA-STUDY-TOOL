#!/usr/bin/env python3
"""Read-only full comparison of a legacy index against a fresh extraction.

This establishes passage equivalence, NOT source-object identity. The original
R2 object SHA-256 must also be verified independently before provenance writes.
"""
import argparse
import json
import os
from pathlib import Path

from import_extraction import read_jsonl, validate


def compare_passages(extraction_dir, db_rows):
    expected = list(read_jsonl(Path(extraction_dir) / "passages.jsonl"))
    observed = list(db_rows)
    if len(expected) != len(observed):
        return {"matched": False, "reason": "passage_count_mismatch",
                "expected": len(expected), "actual": len(observed)}
    for idx, (want, got) in enumerate(zip(expected, observed)):
        if (want["chunk_index"], want["page_start"], want["page_end"], want["content"]) != tuple(got):
            return {"matched": False, "reason": "passage_mismatch",
                    "first_mismatch_chunk": idx}
    return {"matched": True, "passage_count": len(expected)}


def compare_existing(extraction_dir, connection):
    extraction_dir = Path(extraction_dir)
    manifest = validate(extraction_dir)
    with connection.transaction():
        with connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("""
                select id,owner_uid,file_size_bytes,page_count
                from source_library_staging.textbooks
                where r2_key=%s
            """, (manifest["r2_key"],))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Legacy textbook not found")
            textbook_id, owner, size, pages = row
            if str(owner) != manifest["owner_uid"] or size != manifest["size_bytes"] or pages != manifest["pdf_page_count"]:
                raise ValueError("Legacy textbook metadata does not match extraction")
            cur.execute("""
                select chunk_index,page_start,page_end,content
                from source_library_staging.passages
                where textbook_id=%s order by chunk_index
            """, (textbook_id,))
            result = compare_passages(extraction_dir, cur.fetchall())
    return {
        "textbook_id": str(textbook_id),
        "source_sha256_claimed_by_extraction": manifest["sha256"],
        "legacy_passages_match_extraction": result,
        "r2_source_identity_verified": False,
        "provenance_write_authorized": False,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction", type=Path, required=True)
    args = parser.parse_args()
    import psycopg
    url = os.environ.get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL is required")
    with psycopg.connect(url) as conn:
        result = compare_existing(args.extraction, conn)
    print(json.dumps(result, indent=2))
    if not result["legacy_passages_match_extraction"]["matched"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
