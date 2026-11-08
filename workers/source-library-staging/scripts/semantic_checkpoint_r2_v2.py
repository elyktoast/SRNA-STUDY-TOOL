"""Explicit, staging-only encrypted checkpoint transport to Cloudflare R2.

No provider calls. Checkpoints are encrypted before upload, decrypted only in
ephemeral runner storage, and never written to Actions artifacts or logs.
"""
import argparse
import os
import re
import sys
from pathlib import Path

BUCKET = "srna-staging-textbooks"
PREFIX = "private-semantic-checkpoints/canonical-gemini-embedding-001"
KEY = PREFIX + ".jsonl.fernet"


def snapshot_key(snapshot):
    if not isinstance(snapshot, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", snapshot):
        raise ValueError("Invalid snapshot identifier")
    return f"{PREFIX}/snapshots/{snapshot}.jsonl.fernet"
MAX_BYTES = 100_000_000


def transfer(mode, checkpoint, *, env=None, client=None, snapshot=None):
    env = os.environ if env is None else env
    if env.get("STAGING_ONLY") != "true" or env.get("SEMANTIC_CHECKPOINT_R2_OPT_IN") != "true":
        raise ValueError("Explicit staging checkpoint opt-in required")
    if mode not in ("restore", "save"):
        raise ValueError("Invalid checkpoint operation")
    from cryptography.fernet import Fernet
    import boto3
    secret = env.get("SEMANTIC_CHECKPOINT_ENCRYPTION_KEY", "")
    if not secret:
        raise ValueError("Missing checkpoint encryption key")
    cipher = Fernet(secret.encode("ascii"))
    if client is None:
        account = env.get("STAGING_R2_ACCOUNT_ID", "")
        access = env.get("STAGING_R2_ACCESS_KEY_ID", "")
        key = env.get("STAGING_R2_SECRET_ACCESS_KEY", "")
        if not account or not access or not key:
            raise ValueError("Missing staging R2 configuration")
        client = boto3.client("s3", endpoint_url=f"https://{account}.r2.cloudflarestorage.com",
                              aws_access_key_id=access, aws_secret_access_key=key,
                              region_name="auto")
    object_key = snapshot_key(snapshot) if snapshot is not None else KEY
    path = Path(checkpoint)
    if mode == "restore":
        if path.exists():
            raise ValueError("Refusing to overwrite local checkpoint")
        try:
            response = client.get_object(Bucket=BUCKET, Key=object_key)
        except client.exceptions.ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404", "NotFound"):
                return {"restored": False}
            raise
        body = response["Body"]
        try:
            ciphertext = body.read(MAX_BYTES + 1)
        finally:
            body.close()
        if len(ciphertext) > MAX_BYTES:
            raise ValueError("Encrypted checkpoint exceeds size limit")
        plaintext = cipher.decrypt(ciphertext)
        if not plaintext or len(plaintext) > MAX_BYTES:
            raise ValueError("Invalid decrypted checkpoint")
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as stream:
            stream.write(plaintext)
            stream.flush()
            os.fsync(stream.fileno())
        return {"restored": True}
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Missing or oversized checkpoint")
    plaintext = path.read_bytes()
    if not plaintext:
        raise ValueError("Empty checkpoint")
    ciphertext = cipher.encrypt(plaintext)
    # Refuse to overwrite a prior checkpoint; concurrent saves must fail closed.
    try:
        client.head_object(Bucket=BUCKET, Key=object_key)
    except client.exceptions.ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in ("NoSuchKey", "404", "NotFound"):
            raise
    else:
        raise ValueError("Remote checkpoint already exists; overwrite is not authorized")
    client.put_object(Bucket=BUCKET, Key=object_key, Body=ciphertext,
                      ContentType="application/octet-stream",
                      Metadata={"format": "fernet-jsonl-v1"})
    return {"saved": True}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("restore", "save"))
    parser.add_argument("checkpoint")
    parser.add_argument("--snapshot", help="Explicit immutable snapshot ID; required for versioned batches")
    args = parser.parse_args(argv)
    try:
        result = transfer(args.mode, args.checkpoint, snapshot=args.snapshot)
        print({"ok": True, **result})
        return 0
    except Exception:
        print({"ok": False, "error": "CHECKPOINT_TRANSFER_UNAVAILABLE"})
        return 2


if __name__ == "__main__":
    sys.exit(main())
