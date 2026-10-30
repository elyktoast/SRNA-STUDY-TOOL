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


def process(pdf, out, owner_uid, r2_key, apply=False, expected_sha256=None, ocr=False):
    manifest = extract(pdf, out, owner_uid, r2_key, ocr=ocr)
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
    result = {
        "pdf_pages": validated["pdf_page_count"],
        "passages": validated["passage_count"],
        "requires_ocr_review": validated["requires_ocr_review"],
        "ocr_attempted": validated.get("ocr_attempted", False),
        "ocr_pages": validated.get("ocr_pages", []),
        "ocr_failed_pages": validated.get("ocr_failed_pages", []),
        "source_sha256": validated["sha256"],
        "indexed": False,
        "citation_verified": False,
    }
    if apply:
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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(json.dumps(process(args.pdf, args.out, args.owner_uid, args.r2_key, args.apply, ocr=args.ocr), indent=2))


if __name__ == "__main__":
    main()
