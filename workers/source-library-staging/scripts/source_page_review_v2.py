"""Validate human page-review attestations against immutable PDF identity.

Local staging-only JSON records; no database writes or source content exposed.
"""
import json
import re
from pathlib import Path

SHA = re.compile(r"^[0-9a-f]{64}$")
DECISIONS = {"text_verified", "nontext_page_reviewed", "ocr_corrected"}

def load_reviewed_pages(path, manifest):
    if path is None:
        return ()
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise ValueError("Invalid page review record version")
    digest = manifest.get("sha256")
    if not isinstance(digest, str) or not SHA.fullmatch(digest):
        raise ValueError("Valid extraction digest required")
    if document.get("source_sha256") != digest:
        raise ValueError("Page review source digest mismatch")
    if document.get("owner_uid") != manifest.get("owner_uid"):
        raise ValueError("Page review owner mismatch")
    if document.get("r2_key") != manifest.get("r2_key"):
        raise ValueError("Page review source key mismatch")
    reviews = document.get("reviews")
    if not isinstance(reviews, list):
        raise ValueError("Review entries required")
    pages = set()
    for entry in reviews:
        if not isinstance(entry, dict):
            raise ValueError("Invalid review entry")
        page = entry.get("pdf_page")
        if type(page) is not int or not 1 <= page <= manifest["pdf_page_count"] or page in pages:
            raise ValueError("Invalid or duplicate reviewed PDF page")
        if entry.get("decision") not in DECISIONS:
            raise ValueError("Unrecognized review decision")
        if not isinstance(entry.get("reviewer_id"), str) or not entry["reviewer_id"].strip():
            raise ValueError("Reviewer identity required")
        if not isinstance(entry.get("reviewed_at"), str) or not re.fullmatch(
                r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", entry["reviewed_at"]):
            raise ValueError("UTC review timestamp required")
        if not isinstance(entry.get("note"), str) or not entry["note"].strip():
            raise ValueError("Review note required")
        pages.add(page)
    return tuple(sorted(pages))
