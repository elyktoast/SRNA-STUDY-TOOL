"""Staging-only server-side R2 source loader for trusted page inspection.

Use only after reviewer session and protected role authorization. The caller
must independently resolve the trusted extraction manifest; R2 object
metadata is not a substitute for that manifest.
"""
import hashlib
import re
import os
import tempfile
from contextlib import contextmanager

BUCKET = "srna-staging-textbooks"
MAX_BYTES = 512 * 1024 * 1024
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
        if response.get("ContentLength", size) != size:
            raise ValueError("R2 response size differs from verified HEAD")
        if response.get("ETag", head.get("ETag")) != head.get("ETag"):
            raise ValueError("R2 response ETag differs from verified HEAD")
        for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
            if not isinstance(chunk, bytes):
                raise ValueError("R2 returned non-byte content")
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


@contextmanager
def verified_staging_pdf_file(client, *, owner_uid, r2_key, expected_sha256,
                              bucket=BUCKET):
    """Yield a SHA-256 verified temporary PDF path without buffering the source.

    Keep the file private and remove it even when rendering fails. The caller
    must not retain or serve this path beyond the context.
    """
    if bucket != BUCKET:
        raise ValueError("Staging bucket required")
    if (not isinstance(owner_uid, str) or not isinstance(r2_key, str)
            or not OWNER_KEY.fullmatch(r2_key)
            or not r2_key.startswith(owner_uid + "/")):
        raise ValueError("Invalid owner-scoped PDF key")
    if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
        raise ValueError("Trusted source SHA-256 required")
    head = client.head_object(Bucket=bucket, Key=r2_key)
    size = head.get("ContentLength")
    if type(size) is not int or not 5 <= size <= MAX_BYTES:
        raise ValueError("Invalid source size")
    fd, name = tempfile.mkstemp(prefix="staging-review-", suffix=".pdf")
    try:
        digest = hashlib.sha256()
        received = 0
        response = client.get_object(Bucket=bucket, Key=r2_key)
        try:
            if response.get("ContentLength", size) != size:
                raise ValueError("R2 response size differs from verified HEAD")
            if response.get("ETag", head.get("ETag")) != head.get("ETag"):
                raise ValueError("R2 response ETag differs from verified HEAD")
            with os.fdopen(fd, "wb") as output:
                fd = -1
                for chunk in response["Body"].iter_chunks(chunk_size=1024 * 1024):
                    if not isinstance(chunk, bytes):
                        raise ValueError("R2 returned non-byte content")
                    received += len(chunk)
                    if received > size or received > MAX_BYTES:
                        raise ValueError("R2 download exceeded expected size")
                    output.write(chunk)
                    digest.update(chunk)
        finally:
            response["Body"].close()
        if received != size or digest.hexdigest() != expected_sha256:
            raise ValueError("R2 source fingerprint or size mismatch")
        latest = client.head_object(Bucket=bucket, Key=r2_key)
        if latest.get("ContentLength") != size or latest.get("ETag") != head.get("ETag"):
            raise ValueError("R2 source replaced during inspection fetch")
        yield name
    finally:
        if fd >= 0:
            os.close(fd)
        try:
            os.unlink(name)
        except FileNotFoundError:
            pass
