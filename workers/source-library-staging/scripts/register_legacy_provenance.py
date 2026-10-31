#!/usr/bin/env python3
"""Register provenance for an unchanged legacy index, never replace passages.

Requires a private PDF freshly fetched from the exact owner-scoped R2 key.
Default mode is read-only. --apply must be explicitly requested by an operator.
"""
import argparse
import json
import os
from pathlib import Path

from compare_legacy_extraction import compare_passages, verify_pdf
from import_extraction import read_jsonl, validate


def register(folder, pdf_path, connection, *, apply=False, downloaded_sha256=None):
    folder = Path(folder)
    manifest = validate(folder)
    digest = verify_pdf(pdf_path, manifest)
    if downloaded_sha256 is None or digest != downloaded_sha256:
        raise ValueError("Independent R2 download SHA-256 verification required")
    with connection.transaction():
        with connection.cursor() as cur:
            if not apply:
                cur.execute("set transaction read only")
            else:
                cur.execute("select pg_advisory_xact_lock(hashtextextended(%s,0))",
                            ("r2:" + manifest["owner_uid"] + ":" + manifest["r2_key"],))
                cur.execute("select pg_advisory_xact_lock(hashtextextended(%s,0))",
                            ("source-sha:" + manifest["owner_uid"] + ":" + digest,))
            cur.execute("""
                select id, owner_uid, file_size_bytes, page_count
                from source_library_staging.textbooks
                where r2_key=%s
                """ + (" for update" if apply else ""), (manifest["r2_key"],))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Legacy textbook missing")
            tid, owner, size, pages = row
            if (str(owner) != manifest["owner_uid"] or
                    size != manifest["size_bytes"] or
                    pages != manifest["pdf_page_count"]):
                raise ValueError("Textbook owner, size or page count mismatch")
            cur.execute("""
                select chunk_index,page_start,page_end,content
                from source_library_staging.passages
                where textbook_id=%s order by chunk_index
                """ + (" for update" if apply else ""), (tid,))
            comparison = compare_passages(folder, cur.fetchall())
            if not comparison["matched"]:
                raise ValueError("Legacy passages differ; provenance not registered")
            cur.execute("""
                select source_sha256,owner_uid,file_size_bytes,r2_key
                from source_library_staging.source_versions
                where textbook_id=%s
                """, (tid,))
            versions = cur.fetchall()
            for old_digest, old_owner, old_size, old_key in versions:
                if (old_digest != digest or str(old_owner) != str(owner)
                        or old_size != size or old_key != manifest["r2_key"]):
                    raise ValueError("Conflicting source version exists")
            cur.execute("""
                select textbook_id from source_library_staging.source_versions
                where owner_uid=%s and source_sha256=%s and r2_key<>%s
                limit 1
                """, (owner, digest, manifest["r2_key"]))
            if cur.fetchone():
                raise ValueError("Same source digest already assigned to another key")
            if apply and not versions:
                cur.execute("""
                    insert into source_library_staging.source_versions
                    (textbook_id,owner_uid,source_sha256,file_size_bytes,r2_key)
                    values (%s,%s,%s,%s,%s)
                    on conflict (textbook_id,source_sha256) do nothing
                    """, (tid, owner, digest, size, manifest["r2_key"]))
            return {"matched_passages": comparison["passage_count"],
                    "pdf_digest_verified": True,
                    "provenance_registered": bool(apply and not versions),
                    "already_registered": bool(versions)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extraction", type=Path, required=True)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--r2-download-sha256", required=True,
                        help="SHA-256 returned by the authenticated R2 fetch operation")
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly register matching provenance in staging")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        parser.error("DATABASE_URL required")
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = register(args.extraction, args.pdf, conn, apply=args.apply,
                          downloaded_sha256=args.r2_download_sha256)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
