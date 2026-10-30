#!/usr/bin/env python3
"""Offline, staging-only R2 chapter proposal audit; no database writes.

Outputs only counts and PDF page numbers. Headings and textbook text stay in
temporary local files, never GitHub logs.
"""
import argparse
import json
import os
import re
import tempfile
from pathlib import Path

from extract_textbook import extract
from process_r2_textbook import BUCKET, fetch_r2
from propose_chapters import propose
from propose_layout_chapters import propose_layout

OWNER_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def audit(owner_uid, key, client, ocr=False):
    if not OWNER_RE.fullmatch(owner_uid):
        raise ValueError("Invalid owner UUID")
    if not isinstance(key, str) or not key.startswith(owner_uid + "/") or not re.fullmatch(
            r"[A-Za-z0-9._-]{1,150}\.pdf", Path(key).name, re.I):
        raise ValueError("Invalid owner-scoped R2 key")
    with tempfile.TemporaryDirectory(prefix="srna-chapter-audit-") as tmp:
        root = Path(tmp)
        pdf = root / Path(key).name
        expected = fetch_r2(pdf, owner_uid, key, client, bucket=BUCKET)
        manifest = extract(pdf, root / "extracted", owner_uid, key, ocr=ocr)
        if manifest["sha256"] != expected["sha256"]:
            raise ValueError("R2 integrity check failed")
        with (root / "extracted" / "pages.jsonl").open(encoding="utf-8") as handle:
            candidates = propose(json.loads(line) for line in handle if line.strip())
        layout = propose_layout(pdf)
        return {"status": "review_only", "pdf_pages": manifest["pdf_page_count"],
                "candidate_count": len(candidates),
                "layout_candidate_count": len(layout),
                "layout_candidate_pdf_pages": [c["pdf_page"] for c in layout],
                "candidate_pdf_pages": [c["pdf_page"] for c in candidates],
                "citation_verified": False, "database_written": False}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--r2-key", required=True)
    parser.add_argument("--ocr", action="store_true")
    args = parser.parse_args()
    import boto3
    client = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    print(json.dumps(audit(args.owner_uid, args.r2_key, client, args.ocr), indent=2))


if __name__ == "__main__":
    main()
