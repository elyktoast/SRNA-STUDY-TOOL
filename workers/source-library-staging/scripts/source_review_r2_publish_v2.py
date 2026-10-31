"""Operator-only staging R2 queue publisher; never callable from a browser.

Downloads the current R2 PDF, verifies its bytes against the extraction manifest,
and publishes the review queue without modifying or replacing the original PDF.
Uses a separate immutable SHA-256 attestation sidecar so that the original R2
object metadata and content remain untouched.
"""
import argparse
import hashlib
import os
import json
import tempfile
from pathlib import Path

from source_review_queue_publish_v2 import prepare_queue_artifacts

MAX_BYTES = 300 * 1024 * 1024


def publish_verified_queue(client, bucket, pdf_key, extraction_dir, *, apply=False):
    if bucket != "srna-staging-textbooks":
        raise ValueError("Staging bucket required")
    extraction_dir = Path(extraction_dir)
    manifest = json.loads((extraction_dir / "manifest.json").read_text(encoding="utf-8"))
    if pdf_key != manifest.get("r2_key"):
        raise ValueError("R2 key does not match extraction")
    head = client.head_object(Bucket=bucket, Key=pdf_key)
    size = head.get("ContentLength")
    if type(size) is not int or not 5 <= size <= MAX_BYTES:
        raise ValueError("Invalid source object size")
    if size != manifest.get("size_bytes"):
        raise ValueError("R2 source size differs from extraction")
    with tempfile.TemporaryDirectory(prefix="srna-verified-review-") as temp:
        local = Path(temp) / manifest["filename"]
        digest = hashlib.sha256()
        response = client.get_object(Bucket=bucket, Key=pdf_key)
        received = 0
        try:
            with local.open("wb") as output:
                for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                    if not chunk:
                        continue
                    received += len(chunk)
                    if received > size:
                        raise ValueError("R2 source exceeded expected size")
                    digest.update(chunk)
                    output.write(chunk)
        finally:
            response["Body"].close()
        if received != size or digest.hexdigest() != manifest.get("sha256"):
            raise ValueError("R2 source fingerprint mismatch")
        artifacts = prepare_queue_artifacts(local, extraction_dir)
        queue_key = artifacts["queue_r2_key"]
        attestation_key = queue_key + ".source.json"
        if apply:
            # Re-read source immediately before publication. This catches normal
            # concurrent replacements, but cannot provide atomicity across keys.
            current = client.head_object(Bucket=bucket, Key=pdf_key)
            if current.get("ETag") != head.get("ETag") or current.get("ContentLength") != size:
                raise ValueError("R2 source changed before publication")
            attestation = json.dumps({
                "schema_version": 1, "r2_key": pdf_key,
                "source_sha256": artifacts["pdf_sha256"],
                "source_etag": head.get("ETag"),
                "size_bytes": size,
                "queue_sha256": hashlib.sha256(artifacts["queue_json"].encode("utf-8")).hexdigest(),
            }, separators=(",", ":"), sort_keys=True)
            # Invalidate any old attestation first; an interrupted publication
            # must not leave an old proof paired with a newly written queue.
            client.delete_object(Bucket=bucket, Key=attestation_key)
            client.put_object(Bucket=bucket, Key=queue_key,
                              Body=artifacts["queue_json"].encode("utf-8"),
                              ContentType="application/json")
            # Check source identity again after the queue write. If a source
            # replacement occurred, leave the queue unpublished.
            latest = client.head_object(Bucket=bucket, Key=pdf_key)
            if latest.get("ETag") != head.get("ETag") or latest.get("ContentLength") != size:
                raise ValueError("R2 source changed during publication")
            client.put_object(Bucket=bucket, Key=attestation_key,
                              Body=attestation.encode("utf-8"),
                              ContentType="application/json")
        return {"queue_r2_key": queue_key, "attestation_r2_key": attestation_key,
                "source_sha256": artifacts["pdf_sha256"], "published": bool(apply),
                "approval_enabled": False}

def main():
    parser = argparse.ArgumentParser(description="Publish a verified staging PDF review queue")
    parser.add_argument("--r2-key", required=True, help="Owner-scoped original PDF object key")
    parser.add_argument("--extraction-dir", type=Path, required=True, help="Local trusted extraction directory containing manifest.json")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="Verify bytes and produce publication plan; no writes")
    mode.add_argument("--apply", action="store_true", help="Publish queue and source attestation to staging R2")
    args = parser.parse_args()
    import boto3
    account = os.environ["R2_ACCOUNT_ID"]
    client = boto3.client(
        "s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto",
    )
    result = publish_verified_queue(client, "srna-staging-textbooks", args.r2_key,
                                    args.extraction_dir, apply=args.apply)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
