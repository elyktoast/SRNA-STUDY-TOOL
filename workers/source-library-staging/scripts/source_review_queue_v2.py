"""Build a safe reviewer queue from a trusted extraction manifest.

No page text, copyrighted images, approvals, or database mutations are emitted.
The caller must load the manifest from its verified server-side source, not a
browser payload. Physical PDF pages are one-based.
"""
import re

SHA256 = re.compile(r"^[0-9a-f]{64}$")
CATEGORIES = frozenset({
    "ocr_error", "image_content_review", "short_text_review",
    "blank_candidate_review",
})

def build_review_queue(manifest):
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise ValueError("Trusted extraction manifest required")
    owner = manifest.get("owner_uid")
    key = manifest.get("r2_key")
    digest = manifest.get("sha256")
    count = manifest.get("pdf_page_count")
    if not isinstance(owner, str) or not re.fullmatch(
        r"[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}", owner, re.I):
        raise ValueError("Invalid source owner")
    if not isinstance(key, str) or not key.startswith(owner + "/") or not key.endswith(".pdf") or ".." in key:
        raise ValueError("Invalid source key")
    if not isinstance(digest, str) or not SHA256.fullmatch(digest):
        raise ValueError("Invalid source fingerprint")
    if type(count) is not int or count < 1:
        raise ValueError("Invalid PDF page count")
    details = manifest.get("low_text_details")
    pages = manifest.get("low_text_pages")
    if not isinstance(details, list) or not isinstance(pages, list):
        raise ValueError("Missing extraction review details")
    if len(details) != len(pages) or len(set(pages)) != len(pages):
        raise ValueError("Inconsistent review pages")
    result = []
    seen = set()
    for detail in details:
        if not isinstance(detail, dict):
            raise ValueError("Invalid page detail")
        page = detail.get("pdf_page")
        category = detail.get("review_category")
        if type(page) is not int or page < 1 or page > count or page in seen or page not in pages:
            raise ValueError("Invalid or duplicate physical PDF page")
        if category not in CATEGORIES:
            raise ValueError("Unknown review category")
        characters = detail.get("characters")
        if type(characters) is not int or characters < 0:
            raise ValueError("Invalid extracted character count")
        seen.add(page)
        result.append({"pdf_page": page, "review_category": category,
                       "characters": characters, "ocr_failed": detail.get("ocr_failed") is True,
                       "has_images": detail.get("has_images") is True})
    if seen != set(pages):
        raise ValueError("Incomplete review page inventory")
    return {"source_sha256": digest, "r2_key": key, "pdf_page_count": count,
            "pages": sorted(result, key=lambda item: item["pdf_page"]),
            "approval_enabled": False}
