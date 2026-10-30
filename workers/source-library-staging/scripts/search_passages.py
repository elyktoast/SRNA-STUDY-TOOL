#!/usr/bin/env python3
"""Private, read-only full-text search for staged textbook passages.

Requires psycopg[binary]. DATABASE_URL must be a trusted server-side credential.
Never expose this script or the database credential to student browsers.
"""
import argparse
import json
import os


def search(conn, query, owner_uid, limit=10, textbook_id=None, section_id=None,
           include_subsections=False):
    if not query or not query.strip():
        raise ValueError("Search query required")
    if not 1 <= limit <= 50:
        raise ValueError("Limit must be 1..50")
    if include_subsections and not section_id:
        raise ValueError("Section ID required to include subsections")
    sql = """
      select p.id::text, t.id::text, t.filename, p.chunk_index,
             p.page_start, p.page_end, s.id::text, s.heading,
             ts_rank_cd(p.content_search, websearch_to_tsquery('english', %s)) as rank,
             left(p.content, 1200) as excerpt
        from source_library_staging.passages p
        join source_library_staging.textbooks t on t.id=p.textbook_id
        left join source_library_staging.sections s on s.id=p.section_id
       where t.owner_uid=%s
         and t.status='ready'
         and p.content_search @@ websearch_to_tsquery('english', %s)
    """
    params = [query, owner_uid, query]
    if textbook_id:
        sql += " and t.id=%s::uuid"
        params.append(textbook_id)
    if section_id:
        if include_subsections:
            sql += """ and p.section_id in (
              with recursive descendants as (
                select s0.id, s0.textbook_id from source_library_staging.sections s0
                join source_library_staging.textbooks t0 on t0.id=s0.textbook_id
                where s0.id=%s::uuid and t0.owner_uid=%s and t0.status='ready'
                union all
                select child.id, child.textbook_id
                  from source_library_staging.sections child
                  join descendants parent on child.parent_section_id=parent.id
                 and child.textbook_id=parent.textbook_id
              ) select id from descendants
            )"""
            params.extend([section_id, owner_uid])
        else:
            sql += " and p.section_id=%s::uuid"
            params.append(section_id)
    sql += " order by rank desc, t.id, p.chunk_index limit %s"
    params.append(limit)
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return [
            {"passage_id": r[0], "textbook_id": r[1], "filename": r[2],
             "chunk_index": r[3], "pdf_page_start": r[4], "pdf_page_end": r[5],
             "section_id": r[6], "section_heading": r[7],
             "rank": float(r[8]), "excerpt": r[9],
             "citation_verified": False, "page_numbering": "physical_pdf_page_1_based"}
            for r in cur.fetchall()
        ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--textbook-id")
    parser.add_argument("--section-id")
    parser.add_argument("--include-subsections", action="store_true")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL required")
    import psycopg
    with psycopg.connect(url) as conn:
        rows = search(conn, args.query, args.owner_uid, args.limit, args.textbook_id, args.section_id,
                      args.include_subsections)
    print(json.dumps({"results": rows, "note": "PDF page references are not verified printed-page citations"}, indent=2))


if __name__ == "__main__":
    main()
