"""Conservative source-extraction quality gate for staging.

A ready extraction is not a verified textbook citation. Human review is
required for unresolved OCR and visually significant low-text pages.
"""
def assess(manifest, *, reviewed_pages=()):
    if not isinstance(manifest, dict):
        raise ValueError("Extraction manifest required")
    count = manifest.get("pdf_page_count")
    if type(count) is not int or count < 1:
        raise ValueError("Valid PDF page count required")
    if manifest.get("status") != "extracted_not_indexed":
        raise ValueError("Expected unindexed extraction manifest")
    if manifest.get("page_numbering") != "physical_pdf_page_1_based":
        raise ValueError("Physical PDF page numbering required")
    if manifest.get("citation_verified") is not False:
        raise ValueError("Extraction must not claim verified citations")
    if type(manifest.get("passage_count")) is not int or manifest["passage_count"] < 1:
        raise ValueError("No searchable passages")
    categories = ("low_text_pages", "ocr_failed_pages")
    for name in categories:
        pages = manifest.get(name, [])
        if not isinstance(pages, list) or any(type(p) is not int or p < 1 or p > count for p in pages):
            raise ValueError("Invalid " + name)
    if not isinstance(reviewed_pages, (tuple, list, set)) or any(
        type(p) is not int or p < 1 or p > count for p in reviewed_pages
    ):
        raise ValueError("Invalid reviewed page list")
    if manifest.get("ocr_attempted") is not True and manifest.get("ocr_pages"):
        raise ValueError("OCR recovery without OCR attempt")
    unresolved = sorted((set(manifest.get("low_text_pages", [])) |
                         set(manifest.get("ocr_failed_pages", []))) - set(reviewed_pages))
    return {
        "ready_for_unqualified_indexing": not unresolved,
        "requires_source_review": bool(unresolved),
        "unresolved_pdf_pages": unresolved,
        "reviewed_pdf_pages": sorted(set(reviewed_pages)),
        "printed_page_citations_verified": False,
        "recommendation": "manual_review" if unresolved else "eligible_for_indexing",
    }
