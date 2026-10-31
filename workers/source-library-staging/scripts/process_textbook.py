#!/usr/bin/env python3
"""Run local PDF extraction, validate the index, and optionally import it.

Staging only. Does not fetch R2 objects or run automatically on upload.
Requires PyMuPDF; --apply additionally requires psycopg and DATABASE_URL.
Example:
 python process_textbook.py book.pdf --owner-uid UUID --r2-key UUID/book.pdf --out ./index --dry-run
 python process_textbook.py book.pdf --owner-uid UUID --r2-key UUID/book.pdf --out ./index --apply
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from extract_textbook import extract
from import_extraction import import_passages, validate
from source_extraction_quality_v2 import assess
from source_page_review_v2 import load_reviewed_pages


def process(pdf, out, owner_uid, r2_key, apply=False, expected_sha256=None, ocr=False, review_images=False, reviewed_pages=(), page_review_file=None):
    manifest = extract(pdf, out, owner_uid, r2_key, ocr=ocr, review_images=review_images)
    validated = validate(out)
    if expected_sha256 is not None and validated["sha256"] != expected_sha256:
        raise ValueError("Extracted PDF digest differs from original R2 download")
    if validated["sha256"] != manifest["sha256"]:
        raise ValueError("Extraction manifest changed during validation")
    # Verify the source bytes again before any database write. A manifest alone
    # cannot establish that passages came from the current source PDF.
    with pdf.open("rb") as source:
        current_sha256 = hashlib.file_digest(source, "sha256").hexdigest()
    if current_sha256 != validated["sha256"]:
        raise ValueError("Source PDF changed after extraction; refusing import")
    if apply and reviewed_pages:
        raise ValueError('Unattested --reviewed-page values cannot authorize indexing; use --page-review-file')
    verified_pages = load_reviewed_pages(page_review_file, validated) if page_review_file else ()
    quality = assess(validated, reviewed_pages=verified_pages if apply else tuple(set(verified_pages) | set(reviewed_pages)))
    result = {
        "extraction_quality": quality,
        "pdf_pages": validated["pdf_page_count"],
        "passages": validated["passage_count"],
        "requires_ocr_review": validated["requires_ocr_review"],
        "low_text_pages": validated.get("low_text_pages", []),
        "low_text_details": validated.get("low_text_details", []),
        "ocr_attempted": validated.get("ocr_attempted", False),
        "ocr_pages": validated.get("ocr_pages", []),
        "ocr_failed_pages": validated.get("ocr_failed_pages", []),
        "source_sha256": validated["sha256"],
        "visual_review_available_locally": bool(review_images),
        "indexed": False,
        "citation_verified": False,
    }
    if apply:
        if not quality["ready_for_unqualified_indexing"]:
            raise ValueError("Unresolved OCR or low-text pages require documented review before indexing")
        url = os.environ.get("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL required for --apply")
        import psycopg
        with psycopg.connect(url, autocommit=False) as conn:
            result["textbook_id"] = import_passages(out, validated, conn)
        result["indexed"] = True
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--r2-key", required=True)
    parser.add_argument("--ocr", action="store_true", help="Attempt Tesseract OCR on low-text pages")
    parser.add_argument("--review-images", action="store_true", help="Generate local visual-review PNGs; do not upload to GitHub")
    parser.add_argument("--reviewed-page", type=int, action="append", default=[],
                        help="PDF page manually reviewed against original; repeat per page")
    parser.add_argument("--page-review-file", type=Path,
                        help="Source-bound JSON attestations for reviewed PDF pages")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(process(args.pdf, args.out, args.owner_uid, args.r2_key, args.apply, ocr=args.ocr, review_images=args.review_images, reviewed_pages=args.reviewed_page, page_review_file=args.page_review_file), indent=2))


if __name__ == "__main__":
    main()
