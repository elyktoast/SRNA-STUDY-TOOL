"""Server-only source-bound PDF page inspection orchestration.

The storage adapter must fetch a source by a server-resolved owner-scoped key.
The manifest must be independently obtained from trusted server storage, never
from a browser request. This module never issues approval receipts.
"""
import hashlib
import re

from source_review_page_render_v2 import render_verified_pdf_page


def load_verified_review_page(*, owner_uid, r2_key, pdf_page, manifest_loader,
                              source_loader):
    """Return immutable source-bound PNG and digest, or fail closed.

    manifest_loader(owner_uid, r2_key) returns trusted server-side metadata.
    source_loader(owner_uid, r2_key) returns the original PDF bytes from R2.
    The caller must authenticate the reviewer and verify owner/admin role
    before invoking either adapter; the response must not be cached publicly.
    """
    if not isinstance(owner_uid, str) or re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", owner_uid
    ) is None:
        raise ValueError("Invalid owner identity")
    if (not isinstance(r2_key, str) or not r2_key.startswith(owner_uid + "/")
            or any(part in ("", ".", "..") for part in r2_key.split("/"))
            or chr(92) in r2_key or any(ord(char) < 32 or ord(char) == 127 for char in r2_key)):
        raise ValueError("Invalid owner-scoped R2 key")
    if type(pdf_page) is not int or pdf_page < 1:
        raise ValueError("Invalid physical PDF page")
    if not callable(manifest_loader) or not callable(source_loader):
        raise ValueError("Trusted source adapters required")
    manifest = manifest_loader(owner_uid, r2_key)
    if not isinstance(manifest, dict) or manifest.get("owner_uid") != owner_uid or manifest.get("r2_key") != r2_key:
        raise ValueError("Trusted source manifest identity mismatch")
    expected = manifest.get("sha256")
    count = manifest.get("pdf_page_count")
    if not isinstance(expected, str) or re.fullmatch(r"[0-9a-f]{64}", expected) is None:
        raise ValueError("Trusted source fingerprint missing")
    if type(count) is not int or count < 1 or pdf_page > count:
        raise ValueError("Physical PDF page outside trusted manifest")
    source = source_loader(owner_uid, r2_key)
    if not isinstance(source, bytes):
        raise ValueError("Trusted source loader returned invalid PDF")
    image, digest = render_verified_pdf_page(
        source, expected_source_sha256=expected, pdf_page=pdf_page)
    return {"png": image, "image_sha256": digest, "source_sha256": expected,
            "owner_uid": owner_uid, "r2_key": r2_key, "pdf_page": pdf_page}
