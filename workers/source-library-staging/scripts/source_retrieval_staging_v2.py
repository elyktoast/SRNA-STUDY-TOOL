"""Server-side, staging-only passage retrieval with source- and page-scoped filtering.

Never expose this query through a browser without independently verified admin identity.
PDF page references are physical one-based pages, not verified textbook print pages.
"""
import re
from uuid import UUID


def search_passages(conn, *, owner_uid, textbook_id, query, chapter_id=None,
                    page_start=None, page_end=None, limit=20):
    """Return matching passages using bounded PostgreSQL full-text ranking.

    Restrict by owner, exact textbook, and optional section or physical page range.
    Callers must separately authorize the operator before invoking this function.
    """
    for name, value in (("owner_uid", owner_uid), ("textbook_id", textbook_id)):
        if not isinstance(value, str):
            raise ValueError("Invalid " + name)
        try:
            if str(UUID(value)) != value.lower():
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValueError("Invalid " + name) from None
    if chapter_id is not None:
        if not isinstance(chapter_id, str):
            raise ValueError("Invalid chapter_id")
        try:
            if str(UUID(chapter_id)) != chapter_id.lower():
                raise ValueError()
        except (ValueError, AttributeError):
            raise ValueError("Invalid chapter_id") from None
    if not isinstance(query, str) or not 2 <= len(query.strip()) <= 200:
        raise ValueError("Invalid retrieval query")
    if not re.search(r"\w", query, re.UNICODE):
        raise ValueError("Invalid retrieval query")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Invalid result limit")
    for value in (page_start, page_end):
        if value is not None and (type(value) is not int or not 1 <= value <= 100000):
            raise ValueError("Invalid physical PDF page")
    if page_start is not None and page_end is not None and page_start > page_end:
        raise ValueError("Invalid page range")

    sql = """
        SELECT p.chunk_index, p.page_start, p.page_end, p.content,
               p.section_id, ts_rank_cd(
                   to_tsvector('english', p.content),
                   websearch_to_tsquery('english', %s)) AS rank
        FROM source_library_staging.passages AS p
        JOIN source_library_staging.textbooks AS t ON t.id = p.textbook_id
        WHERE t.owner_uid = %s::uuid AND t.id = %s::uuid AND t.status = 'ready'
          AND to_tsvector('english', p.content) @@ websearch_to_tsquery('english', %s)
    """
    params = [query, owner_uid, textbook_id, query]
    if chapter_id is not None:
        sql += """ AND p.section_id = %s::uuid
            AND EXISTS (SELECT 1 FROM source_library_staging.sections s
                        WHERE s.id = p.section_id AND s.textbook_id = t.id)
            AND EXISTS (SELECT 1 FROM source_library_staging.source_versions v
                        WHERE v.textbook_id = t.id AND v.owner_uid = t.owner_uid)"""
        params.append(chapter_id)
    if page_start is not None:
        sql += " AND p.page_end >= %s"
        params.append(page_start)
    if page_end is not None:
        sql += " AND p.page_start <= %s"
        params.append(page_end)
    sql += " ORDER BY rank DESC, p.page_start ASC, p.chunk_index ASC LIMIT %s"
    params.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, tuple(params))
        rows = cur.fetchall()
    return [{"chunk_index": r[0], "page_start": r[1], "page_end": r[2],
             "content": r[3], "section_id": str(r[4]) if r[4] else None,
             "rank": float(r[5])} for r in rows]


def audit_textbook_retrieval(conn, *, owner_uid, textbook_id):
    """Read-only provenance readiness; ready text does not prove chapter citations."""
    for name, value in (("owner_uid", owner_uid), ("textbook_id", textbook_id)):
        if not isinstance(value, str):
            raise ValueError("Invalid " + name)
        try:
            if str(UUID(value)) != value.lower():
                raise ValueError()
        except ValueError:
            raise ValueError("Invalid " + name) from None
    sql = """
        SELECT t.status, t.page_count,
               (SELECT count(*) FROM source_library_staging.passages p
                WHERE p.textbook_id=t.id),
               (SELECT count(*) FROM source_library_staging.sections s
                WHERE s.textbook_id=t.id),
               (SELECT count(*) FROM source_library_staging.passages p
                WHERE p.textbook_id=t.id AND p.section_id IS NOT NULL),
               (SELECT count(*) FROM source_library_staging.source_versions v
                WHERE v.textbook_id=t.id AND v.owner_uid=t.owner_uid)
        FROM source_library_staging.textbooks t
        WHERE t.id=%s::uuid AND t.owner_uid=%s::uuid
    """
    with conn.cursor() as cur:
        cur.execute(sql, (textbook_id, owner_uid))
        record = cur.fetchone()
    if not record:
        raise ValueError("Textbook not available to owner")
    status, pages, passages, chapters, linked, versions = record
    return {
        "text_search_ready": status == "ready" and passages > 0,
        "chapter_filter_ready": status == "ready" and chapters > 0 and linked > 0 and versions > 0,
        "source_provenance_ready": versions > 0,
        "chapter_publication_ready": status == "ready" and passages > 0 and chapters == 0 and versions > 0,
        "physical_page_reference_ready": status == "ready" and pages > 0 and passages > 0,
        "pdf_page_count": pages, "passage_count": passages,
        "chapter_count": chapters, "chapter_linked_passage_count": linked,
        "source_version_count": versions,
        "print_page_citations_verified": False,
    }
