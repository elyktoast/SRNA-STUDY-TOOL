"""Validate human-verified chapter boundaries before associating indexed passages.

This module does not infer headings from OCR, extract textbook content, or write to DB.
Physical PDF pages are 1-based; printed textbook pages are not assumed equal.
"""


def validate_chapter_boundaries(boundaries, *, pdf_page_count):
    if type(pdf_page_count) is not int or pdf_page_count < 1:
        raise ValueError("Invalid PDF page count")
    if not isinstance(boundaries, list) or not boundaries:
        raise ValueError("At least one reviewed chapter boundary required")
    if len(boundaries) > 2000:
        raise ValueError("Excessive chapter count")
    approved = []
    previous = 0
    for item in boundaries:
        if not isinstance(item, dict) or set(item) != {"heading", "start_page", "verified_against_pdf"}:
            raise ValueError("Invalid chapter boundary structure")
        heading, start, reviewed = item["heading"], item["start_page"], item["verified_against_pdf"]
        if not isinstance(heading, str) or not heading.strip() or len(heading) > 240:
            raise ValueError("Invalid chapter heading")
        if type(start) is not int or not previous < start <= pdf_page_count:
            raise ValueError("Chapter pages must be strictly increasing physical PDF pages")
        if reviewed is not True:
            raise ValueError("Chapter boundary requires explicit source verification")
        approved.append({"heading": heading.strip(), "start_page": start,
                         "verified_against_pdf": True})
        previous = start
    return approved


def assign_passages_to_chapters(passages, boundaries, *, pdf_page_count):
    """Return chapter indexes; pages before first reviewed boundary stay unassigned."""
    reviewed = validate_chapter_boundaries(boundaries, pdf_page_count=pdf_page_count)
    if not isinstance(passages, list):
        raise ValueError("Invalid passage list")
    result = []
    for p in passages:
        if not isinstance(p, dict):
            raise ValueError("Invalid passage")
        start, end = p.get("page_start"), p.get("page_end")
        if (type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= pdf_page_count):
            raise ValueError("Invalid passage page reference")
        matching = [i for i, item in enumerate(reviewed) if item["start_page"] <= start]
        chapter_index = matching[-1] if matching else None
        # Cross-boundary chunks are ambiguous; do not silently attach them.
        if chapter_index is not None and chapter_index + 1 < len(reviewed):
            if end >= reviewed[chapter_index + 1]["start_page"]:
                chapter_index = None
        result.append(chapter_index)
    return result


def persist_verified_chapters(conn, *, owner_uid, textbook_id, boundaries,
                              authenticated_reviewer_uid, reviewer_is_admin=False,
                              expected_source_sha256=None):
    """Operator-only transaction; refuse overwrite, stale source, and unreviewed boundaries.

    This is intentionally not a web endpoint. Caller must independently authenticate
    the reviewer and verify each heading and physical page against the original PDF.
    """
    from uuid import UUID
    import re
    for name, value in (("owner_uid", owner_uid), ("textbook_id", textbook_id),
                        ("authenticated_reviewer_uid", authenticated_reviewer_uid)):
        if not isinstance(value, str):
            raise ValueError("Invalid " + name)
        try:
            if str(UUID(value)) != value.lower():
                raise ValueError()
        except ValueError:
            raise ValueError("Invalid " + name) from None
    if reviewer_is_admin is not True:
        raise PermissionError("Trusted admin reviewer required")
    if not isinstance(expected_source_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", expected_source_sha256):
        raise ValueError("Verified source fingerprint required")
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                """SELECT page_count, status FROM source_library_staging.textbooks
                   WHERE id=%s::uuid AND owner_uid=%s::uuid FOR UPDATE""",
                (textbook_id, owner_uid))
            row = cur.fetchone()
            if not row or row[1] != "ready":
                raise ValueError("Owner-scoped ready textbook required")
            reviewed = validate_chapter_boundaries(boundaries, pdf_page_count=row[0])
            cur.execute(
                """SELECT v.source_sha256
                   FROM source_library_staging.source_versions v
                   JOIN source_library_staging.textbooks t ON t.id=v.textbook_id
                   WHERE v.textbook_id=%s::uuid AND v.owner_uid=%s::uuid
                     AND v.r2_key=t.r2_key AND v.file_size_bytes=t.file_size_bytes
                   ORDER BY v.recorded_at DESC, v.id DESC LIMIT 1""",
                (textbook_id, owner_uid))
            digest_row = cur.fetchone()
            if not digest_row or digest_row[0] != expected_source_sha256:
                raise ValueError("Source fingerprint mismatch")
            cur.execute(
                """SELECT count(*) FROM source_library_staging.sections
                   WHERE textbook_id=%s::uuid""", (textbook_id,))
            if cur.fetchone()[0] != 0:
                raise ValueError("Existing chapters require explicit migration; refusing overwrite")
            cur.execute(
                """SELECT chunk_index, page_start, page_end
                   FROM source_library_staging.passages
                   WHERE textbook_id=%s::uuid ORDER BY chunk_index FOR UPDATE""",
                (textbook_id,))
            passages = cur.fetchall()
            if not passages:
                raise ValueError("No indexed passages")
            mapping = assign_passages_to_chapters(
                [{"page_start": p[1], "page_end": p[2]} for p in passages],
                reviewed, pdf_page_count=row[0])
            ids = []
            for order, section in enumerate(reviewed):
                cur.execute(
                    """INSERT INTO source_library_staging.sections
                       (textbook_id, parent_section_id, heading, section_order, start_page)
                       VALUES (%s::uuid, NULL, %s, %s, %s) RETURNING id""",
                    (textbook_id, section["heading"], order, section["start_page"]))
                ids.append(cur.fetchone()[0])
            for (chunk, _, _), chapter_index in zip(passages, mapping):
                if chapter_index is not None:
                    cur.execute(
                        """UPDATE source_library_staging.passages SET section_id=%s::uuid
                           WHERE textbook_id=%s::uuid AND chunk_index=%s""",
                        (str(ids[chapter_index]), textbook_id, chunk))
            return {"chapters_created": len(ids),
                    "passages_linked": sum(i is not None for i in mapping),
                    "passages_unassigned": sum(i is None for i in mapping),
                    "print_page_citations_verified": False}
