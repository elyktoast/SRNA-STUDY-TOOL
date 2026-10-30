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
from process_r2_textbook import BUCKET, run

OWNER_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def enumerate_keys(client, owner_uid, limit=20):
    if not OWNER_RE.fullmatch(owner_uid):
        raise ValueError("Invalid owner UUID")
    if not 1 <= limit <= 100:
        raise ValueError("Limit must be 1..100")
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=owner_uid + "/"):
        for item in page.get("Contents", []):
            key = item.get("Key", "")
            if key.startswith(owner_uid + "/") and key.lower().endswith(".pdf") and ".." not in key:
                keys.append(key)
                if len(keys) >= limit:
                    return keys
    return keys


def process_backlog(client, owner_uid, limit=20, apply=False):
    results = []
    for key in enumerate_keys(client, owner_uid, limit):
        try:
            result = run(owner_uid, key, apply=apply, client=client)
            results.append({"key": key, "ok": True, "result": result})
        except Exception as exc:
            # Do not include connection strings, secret-bearing exception text, or file contents.
            results.append({"key": key, "ok": False, "error_type": type(exc).__name__})
    return {"mode": "apply" if apply else "dry-run", "results": results,
            "succeeded": sum(bool(x["ok"]) for x in results),
            "failed": sum(not x["ok"] for x in results)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--apply", action="store_true",
                        help="Explicitly import into private staging Supabase schema")
    args = parser.parse_args()
    import boto3
    client = boto3.client(
        "s3", endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    print(json.dumps(process_backlog(client, args.owner_uid, args.limit, args.apply), indent=2))


if __name__ == "__main__":
    main()
