"""Staging-only guarded registration of a verified legacy R2 source.

This code is NOT an API endpoint. Run only in a trusted operator workflow after
the R2 PDF and attestation have been independently checked against the current
object; never accept client-provided provenance or guessed source text.
"""
import re
from uuid import UUID
from source_legacy_passage_comparison_v2 import (
    compare_indexed_passages, assess_provenance_backfill_eligibility,
)


def register_verified_legacy_source(
    conn, *, owner_uid, textbook_id, r2_key, source_sha256, source_size_bytes,
    pdf_page_count, fresh_passages, verified_r2_attestation=False,
    extraction_ocr_enabled=False, explicit_operator_approval=False,
):
    for name, value in (("owner_uid", owner_uid), ("textbook_id", textbook_id)):
        try:
            if not isinstance(value, str) or str(UUID(value)) != value.lower():
                raise ValueError()
        except ValueError:
            raise ValueError("Invalid " + name) from None
    if (explicit_operator_approval is not True
            or verified_r2_attestation is not True
            or extraction_ocr_enabled is not True):
        raise PermissionError("Operator approval, trusted R2 attestation and OCR required")
    if (not isinstance(r2_key, str) or not r2_key.startswith(owner_uid + "/")
            or not r2_key.lower().endswith(".pdf") or ".." in r2_key):
        raise ValueError("Invalid owner-scoped source key")
    if not isinstance(source_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", source_sha256):
        raise ValueError("Invalid original R2 source digest")
    if type(source_size_bytes) is not int or source_size_bytes < 5:
        raise ValueError("Invalid original PDF size")
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """SELECT r2_key, file_size_bytes, page_count, status
                   FROM source_library_staging.textbooks
                   WHERE id=%s::uuid AND owner_uid=%s::uuid FOR UPDATE""",
                (textbook_id, owner_uid))
            book = cur.fetchone()
            if (not book or book != (r2_key, source_size_bytes,
                                     pdf_page_count, "ready")):
                raise ValueError("Existing textbook differs from verified R2 source")
            cur.execute(
                """SELECT count(*) FROM source_library_staging.source_versions
                   WHERE textbook_id=%s::uuid OR
                         (owner_uid=%s::uuid AND source_sha256=%s)""",
                (textbook_id, owner_uid, source_sha256))
            if cur.fetchone()[0] != 0:
                raise ValueError("Existing provenance must be reviewed, not overwritten")
        compared = compare_indexed_passages(
            conn, textbook_id=textbook_id, owner_uid=owner_uid,
            fresh_passages=fresh_passages, expected_page_count=pdf_page_count,
            expected_source_sha256=source_sha256)
        eligible = assess_provenance_backfill_eligibility(
            compared, attestation_verified=verified_r2_attestation,
            extraction_ocr_enabled=extraction_ocr_enabled,
            reviewer_confirmed=explicit_operator_approval)
        if not eligible["operator_review_confirmed"]:
            raise ValueError("Fresh extraction does not exactly match stored passages")
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO source_library_staging.source_versions
                   (textbook_id, owner_uid, source_sha256, file_size_bytes, r2_key)
                   VALUES (%s::uuid, %s::uuid, %s, %s, %s)
                   RETURNING id""",
                (textbook_id, owner_uid, source_sha256,
                 source_size_bytes, r2_key))
            if not cur.fetchone():
                raise RuntimeError("Provenance insert not confirmed")
        return {
            "source_version_registered": True,
            "unchanged_passage_count": compared["indexed_passage_count"],
            "chapter_citations_approved": False,
            "printed_page_citations_approved": False,
        }
