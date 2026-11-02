#!/usr/bin/env python3
"""Read-only staging index coverage audit. No PDF content or credentials in output.

Passage coverage does not establish OCR completeness or visual page accuracy.
"""
import argparse
import json
import os
import uuid


def audit(conn, textbook_id):
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("""
                select filename,status,page_count,coalesce(low_text_page_count,0),
                       coalesce(requires_ocr_review,false)
                from source_library_staging.textbooks where id=%s
            """, (textbook_id,))
            book = cur.fetchone()
            if not book:
                raise ValueError("Staging textbook not found")
            filename, status, total, low_text, ocr_flag = book
            if not isinstance(total, int) or total < 1:
                raise ValueError("Invalid PDF page count")
            cur.execute("""
                select page_start,page_end
                from source_library_staging.passages where textbook_id=%s
            """, (textbook_id,))
            ranges = cur.fetchall()
            cur.execute("""
                select (select count(*) from source_library_staging.source_versions where textbook_id=%s),
                       (select count(*) from source_library_staging.sections where textbook_id=%s)
            """, (textbook_id, textbook_id))
            versions, sections = cur.fetchone()
    covered = bytearray(total)
    invalid = 0
    for start, end in ranges:
        if not isinstance(start, int) or not isinstance(end, int) or start < 1 or end < start or end > total:
            invalid += 1
            continue
        covered[start - 1:end] = b"\x01" * (end - start + 1)
    missing = [i + 1 for i, hit in enumerate(covered) if not hit]
    return {
        "textbook_id": str(textbook_id), "filename": filename, "status": status,
        "pdf_pages": total, "passages": len(ranges),
        "covered_pages": total - len(missing), "uncovered_pages": missing,
        "coverage_percent": round(100 * (total - len(missing)) / total, 2),
        "invalid_passage_ranges": invalid,
        "low_text_page_count": low_text, "requires_ocr_review": ocr_flag,
        "source_version_records": versions, "section_records": sections,
        "ready_for_unrestricted_generation": (
            status == "ready" and not missing and not invalid
            and not ocr_flag and versions > 0
        ),
        "next_action": "Visually inspect uncovered/low-text PDF pages, verify R2 digest and OCR before reindexing.",
        "warning": "Coverage means a passage spans a PDF page, not that all page content was extracted."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--textbook-id", required=True, type=uuid.UUID)
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url or os.environ.get("STAGING_ONLY") != "true":
        parser.error("Private staging DATABASE_URL and STAGING_ONLY=true required")
    import psycopg
    with psycopg.connect(url) as conn:
        report = audit(conn, args.textbook_id)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
