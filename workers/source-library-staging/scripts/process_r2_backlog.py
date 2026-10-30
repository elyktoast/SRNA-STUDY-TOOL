#!/usr/bin/env python3
"""Operator-invoked staging backlog indexer (not an automatic upload hook).

Lists R2 PDFs for a single admin owner and processes each through the existing
R2 -> extraction -> private Supabase pipeline. Dry-run by default.
Never place R2 or database credentials in the browser.
"""
import argparse
import json
import os
import re
from pathlib import PurePosixPath
from process_r2_textbook import BUCKET, run

OWNER_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def enumerate_keys(client, owner_uid, limit=20, exclude_keys=None):
    if not isinstance(owner_uid, str) or not OWNER_RE.fullmatch(owner_uid):
        raise ValueError("Invalid owner UUID")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Limit must be 1..100")
    keys = []
    exclude_keys = exclude_keys or set()
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=owner_uid + "/"):
        for item in page.get("Contents", []):
            key = item.get("Key", "")
            if (isinstance(key, str) and key.count("/") == 1 and key.startswith(owner_uid + "/") and key.lower().endswith(".pdf")
                    and ".." not in key and key not in exclude_keys and key not in keys
                    and re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf", PurePosixPath(key).name, re.I)
                    and PurePosixPath(key).name not in (".pdf", "..pdf")):
                keys.append(key)
                if len(keys) >= limit:
                    return keys
    return keys


def indexed_keys(conn, owner_uid):
    """Only ready records are skipped; failed and incomplete uploads can retry."""
    with conn.cursor() as cur:
        cur.execute(
            """select r2_key from source_library_staging.textbooks
               where owner_uid=%s::uuid and status='ready'""",
            (owner_uid,),
        )
        return {row[0] for row in cur.fetchall()}



def assert_staging_schema_ready(conn):
    """Fail before PDF extraction if the provenance migration is missing."""
    with conn.cursor() as cur:
        cur.execute(
            """select to_regclass('source_library_staging.textbooks'),
                      to_regclass('source_library_staging.sections'),
                      to_regclass('source_library_staging.passages'),
                      to_regclass('source_library_staging.source_versions')"""
        )
        tables = cur.fetchone()
        if not tables or any(table is None for table in tables):
            raise RuntimeError("Staging indexing schema incomplete; apply migrations 001-003 first")



def validate_target_key(key, owner_uid):
    """Validate an exact R2 key without listing or reading another owner's files."""
    if (not isinstance(key, str) or key.count("/") != 1
            or not isinstance(owner_uid, str) or not OWNER_RE.fullmatch(owner_uid)
            or not key.startswith(owner_uid + "/") or ".." in key
            or not re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf",
                                PurePosixPath(key).name, re.I)
            or PurePosixPath(key).name in (".pdf", "..pdf")):
        raise ValueError("Invalid owner-scoped PDF key")
    return key


def process_backlog(client, owner_uid, limit=10, apply=False,
                    ready_keys=None, force_reindex=False, ocr=False):
    # Fail fast on invalid inputs even when no R2 objects are returned.
    if not isinstance(owner_uid, str) or not OWNER_RE.fullmatch(owner_uid):
        raise ValueError("Invalid owner UUID")
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Limit must be 1..100")
    if force_reindex and not apply:
        raise ValueError("--force-reindex requires --apply")
    if apply and limit > 10:
        raise ValueError("Apply batch is limited to 10 textbooks")
    results = []
    excluded = ready_keys if not force_reindex else None
    skipped = 0
    pending = []
    seen = set()
    # Scan once: count only valid ready objects and select up to limit pending PDFs.
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=owner_uid + "/"):
        for item in page.get("Contents", []):
            key = item.get("Key")
            if (not isinstance(key, str) or key.count("/") != 1
                    or not key.startswith(owner_uid + "/") or ".." in key
                    or not re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf",
                                        PurePosixPath(key).name, re.I)
                    or PurePosixPath(key).name in (".pdf", "..pdf")):
                continue
            if key in seen:
                continue
            seen.add(key)
            if excluded and key in excluded:
                skipped += 1
            elif len(pending) < limit:
                pending.append(key)
    for key in pending:
        try:
            result = run(owner_uid, key, apply=apply, client=client, ocr=ocr)
            results.append({"key": key, "ok": True, "result": {
                "source_sha256": result.get("source_sha256"),
                "pdf_pages": result.get("pdf_pages"),
                "passages": result.get("passages"),
                "indexed": result.get("indexed"),
                "requires_ocr_review": result.get("requires_ocr_review"),
                                                   "low_text_pages": result.get("low_text_pages", []),
                                                   "low_text_details": result.get("low_text_details", []),
                                                   "low_text_details": result.get("low_text_details", []),
                "ocr_pages_count": len(result.get("ocr_pages", [])),
                "ocr_failed_pages_count": len(result.get("ocr_failed_pages", [])),
                "citation_verified": result.get("citation_verified", False),
            }})
        except Exception as exc:
            # Do not include connection strings, secret-bearing exception text, or file contents.
            results.append({"key": key, "ok": False, "error_type": type(exc).__name__})
    return {"mode": "apply" if apply else "dry-run", "results": results,
            "succeeded": sum(bool(x["ok"]) and not x.get("skipped") for x in results),
            "failed": sum(not x["ok"] for x in results),
            "skipped": skipped}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--r2-key", help="Process exactly one owner-scoped PDF")
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly import into private staging Supabase schema")
    parser.add_argument("--ocr", action="store_true", help="Attempt Tesseract OCR on low-text pages")
    parser.add_argument("--force-reindex", action="store_true",
                        help="Reprocess ready textbooks; use only for intentional reindexing")
    args = parser.parse_args()
    if not OWNER_RE.fullmatch(args.owner_uid):
        parser.error("Invalid owner UUID")
    if not 1 <= args.limit <= 100:
        parser.error("Limit must be 1..100")
    if args.force_reindex and not args.apply:
        parser.error("--force-reindex requires --apply")
    if args.apply and not os.environ.get("DATABASE_URL"):
        parser.error("DATABASE_URL required for --apply")
    if args.apply and args.r2_key is None and args.limit > 10:
        parser.error("Apply batch is limited to 10 textbooks")
    if args.r2_key is not None:
        try:
            validate_target_key(args.r2_key, args.owner_uid)
        except ValueError as exc:
            parser.error(str(exc))
    import boto3
    client = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    ready = None
    # A dry run should also avoid reprocessing already indexed textbooks when
    # the database is configured. Without DATABASE_URL it remains an R2-only
    # extraction check and reports no ready-state exclusions.
    if os.environ.get("DATABASE_URL"):
        import psycopg
        with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
            if args.apply:
                assert_staging_schema_ready(conn)
            if not args.force_reindex:
                ready = indexed_keys(conn, args.owner_uid)
    if args.r2_key is not None:
        key = args.r2_key
        if args.apply and ready is not None and key in ready and not args.force_reindex:
            summary = {"mode": "apply" if args.apply else "dry-run", "results": [],
                       "succeeded": 0, "failed": 0, "skipped": 1}
        else:
            try:
                result = run(args.owner_uid, key, apply=args.apply, client=client, ocr=args.ocr)
                summary = {"mode": "apply" if args.apply else "dry-run",
                           "results": [{"key": key, "ok": True,
                                        "result": {"indexed": result.get("indexed"),
                                                   "passages": result.get("passages"),
                                                   "pdf_pages": result.get("pdf_pages"),
                                                   "source_sha256": result.get("source_sha256"),
                                                   "requires_ocr_review": result.get("requires_ocr_review"),
                                                   "low_text_pages": result.get("low_text_pages", []),
                                                   "ocr_pages_count": len(result.get("ocr_pages", [])),
                                                   "ocr_pages": result.get("ocr_pages", []),
                                                   "ocr_failed_pages_count": len(result.get("ocr_failed_pages", [])),
                                                   "ocr_failed_pages": result.get("ocr_failed_pages", []),
                                                   "citation_verified": False}}],
                           "succeeded": 1, "failed": 0, "skipped": 0}
            except Exception as exc:
                summary = {"mode": "apply" if args.apply else "dry-run",
                           "results": [{"key": key, "ok": False,
                                        "error_type": type(exc).__name__}],
                           "succeeded": 0, "failed": 1, "skipped": 0}
    else:
        summary = process_backlog(client, args.owner_uid, args.limit,
                                  args.apply, ready, args.force_reindex, args.ocr)
    print(json.dumps(summary, indent=2))
    if summary["failed"]:
        raise SystemExit(1)
    if args.apply and not summary["succeeded"] and not summary["skipped"]:
        raise SystemExit("No staging textbooks were indexed")


if __name__ == "__main__":
    main()
