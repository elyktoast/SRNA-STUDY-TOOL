#!/usr/bin/env python3
"""Staging-only R2 -> local PDF -> extraction -> private Supabase index runner.

This is an operator-invoked prototype, NOT a background worker or upload hook.
Environment:
 R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, DATABASE_URL
Dependencies: boto3, pymupdf, psycopg[binary]
Credentials must be server-side and scoped to the staging bucket.
"""
import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from process_textbook import process

MAX_BYTES = 300 * 1024 * 1024
BUCKET = "srna-staging-textbooks"


def fetch_r2(pdf_path, owner_uid, key, client, bucket=BUCKET):
    if (not isinstance(owner_uid, str) or not isinstance(key, str)
            or key.count("/") != 1 or not key.startswith(owner_uid + "/")
            or ".." in key or not re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf",
                                               Path(key).name, re.I)):
        raise ValueError("Invalid owner-scoped R2 key")
    head = client.head_object(Bucket=bucket, Key=key)
    size = head.get("ContentLength")
    if not isinstance(size, int) or not 5 <= size <= MAX_BYTES:
        raise ValueError("Invalid R2 object size")
    digest = hashlib.sha256()
    received = 0
    response = client.get_object(Bucket=bucket, Key=key)
    try:
        with pdf_path.open("wb") as out:
            for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                if not chunk:
                    continue
                received += len(chunk)
                if received > MAX_BYTES or received > size:
                    raise ValueError("R2 object exceeded declared size")
                digest.update(chunk)
                out.write(chunk)
    finally:
        response["Body"].close()
    if received != size:
        raise ValueError("Incomplete R2 download")
    return {"size_bytes": received, "sha256": digest.hexdigest(),
            "original_name": head.get("Metadata", {}).get("name")}


def run(owner_uid, key, apply=False, client=None, ocr=False):
    # Validate the untrusted key before constructing a local download path.
    if (not isinstance(owner_uid, str) or not isinstance(key, str)
            or key.count("/") != 1 or not key.startswith(owner_uid + "/")
            or ".." in key or not re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf", Path(key).name, re.I)
            or Path(key).name in (".pdf", "..pdf")):
        raise ValueError("Invalid owner-scoped R2 PDF key")
    if client is None:
        import boto3
        account = os.environ["R2_ACCOUNT_ID"]
        client = boto3.client(
            "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
            aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
            region_name="auto",
        )
    with tempfile.TemporaryDirectory(prefix="srna-source-staging-") as tmp:
        root = Path(tmp)
        # Keep the R2 object basename as the indexed filename rather than source.pdf.
        # The object key is untrusted: discard directory components.
        source = root / Path(key).name
        expected = fetch_r2(source, owner_uid, key, client)
        # Prefer the original upload filename stored in R2 metadata. Never trust
        # metadata as a path, and keep the source bytes inside this temp folder.
        name = expected.get("original_name")
        if isinstance(name, str) and re.fullmatch(r"[A-Za-z0-9._-]{1,150}\.pdf", name, re.I):
            if name != source.name:
                renamed = root / name
                source.rename(renamed)
                source = renamed
        # Check R2 download integrity before extraction or any database mutation.
        # process() separately rechecks source integrity before import.
        with source.open("rb") as handle:
            local_digest = hashlib.file_digest(handle, "sha256").hexdigest()
        if local_digest != expected["sha256"]:
            raise ValueError("Downloaded PDF changed before extraction")
        result = process(source, root / "index", owner_uid, key, apply=apply,
                         expected_sha256=expected["sha256"], ocr=ocr)
        if result["passages"] < 1:
            raise ValueError("No searchable passages")
        result.update({"r2_key": key, "r2_sha256": expected["sha256"]})
        return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--r2-key", required=True)
    parser.add_argument("--ocr", action="store_true", help="Attempt Tesseract OCR on low-text pages")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.owner_uid, args.r2_key, apply=args.apply, ocr=args.ocr), indent=2))


if __name__ == "__main__":
    main()
