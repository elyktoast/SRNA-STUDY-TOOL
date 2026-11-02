"""Prepare verified review-queue R2 artifacts from a local extracted PDF.

This module does NOT upload, mutate a database, or approve pages. A trusted
server-side operator must independently verify the original R2 PDF bytes,
then publish the returned artifacts together using authenticated R2 tooling.
"""
import hashlib
import json
from pathlib import Path

from source_review_queue_v2 import build_review_queue


def prepare_queue_artifacts(pdf_path, extraction_dir):
    pdf_path = Path(pdf_path)
    extraction_dir = Path(extraction_dir)
    manifest = json.loads((extraction_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("status") != "extracted_not_indexed" or manifest.get("citation_verified") is not False:
        raise ValueError("Untrusted extraction state")
    if pdf_path.name != manifest.get("filename"):
        raise ValueError("PDF filename mismatch")
    if not pdf_path.is_file() or pdf_path.stat().st_size != manifest.get("size_bytes"):
        raise ValueError("PDF missing or size mismatch")
    digest = hashlib.sha256()
    with pdf_path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest() != manifest.get("sha256"):
        raise ValueError("Original PDF digest mismatch")
    queue = build_review_queue(manifest)
    key = queue["r2_key"]
    owner, filename = key.split("/", 1)
    if "/" in filename or filename.startswith("_"):
        raise ValueError("Invalid PDF key for queue storage")
    queue_key = owner + "/_review_queues/" + filename + ".json"
    return {
        "pdf_r2_key": key,
        "pdf_sha256": digest.hexdigest(),
        "queue_r2_key": queue_key,
        "queue_json": json.dumps(queue, separators=(",", ":"), sort_keys=True),
        "pdf_metadata_patch": {"sha256": digest.hexdigest()},
        "approval_enabled": False,
    }
