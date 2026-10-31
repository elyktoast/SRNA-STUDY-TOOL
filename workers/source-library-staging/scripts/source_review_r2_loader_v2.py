"""Staging-only server-side R2 source loader for trusted page inspection.

Use only after reviewer session and protected role authorization. The caller
must independently resolve the trusted extraction manifest; R2 object
metadata is not a substitute for that manifest.
"""
import hashlib
import re

BUCKET = "srna-staging-textbooks"
MAX_BYTES = 75 * 1024 * 1024
OWNER_KEY = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/[A-Za-z0-9._-]{1,150}\.pdf$", re.I)


def fetch_verified_staging_pdf(client, *, owner_uid, r2_key, expected_sha256,
                               bucket=BUCKET):
    if bucket != BUCKET:
        raise ValueError("Staging bucket required")
    if not isinstance(owner_uid, str) or not isinstance(r2_key, str) or not OWNER_KEY.fullmatch(r2_key) or not r2_key.startswith(owner_uid + "/"):
        raise ValueError("Invalid owner-scoped PDF key")
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("Trusted source SHA-256 required")
    head = client.head_object(Bucket=bucket, Key=r2_key)
    size = head.get("ContentLength")
    if type(size) is not int or not 5 <= size <= MAX_BYTES:
        raise ValueError("Invalid source size")
    response = client.get_object(Bucket=bucket, Key=r2_key)
    chunks = []
    received = 0
    digest = hashlib.sha256()
    try:
        for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
            if not chunk:
                continue
            received += len(chunk)
            if received > size or received > MAX_BYTES:
                raise ValueError("R2 download exceeded expected size")
            digest.update(chunk)
            chunks.append(chunk)
    finally:
        response["Body"].close()
    if received != size or digest.hexdigest() != expected_sha256:
        raise ValueError("R2 source fingerprint or size mismatch")
    latest = client.head_object(Bucket=bucket, Key=r2_key)
    if latest.get("ContentLength") != size or latest.get("ETag") != head.get("ETag"):
        raise ValueError("R2 source replaced during inspection fetch")
    return b"".join(chunks)
