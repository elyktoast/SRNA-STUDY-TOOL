#!/usr/bin/env python3
"""Read-only acceptance checks for an existing staging textbook index.

Requires psycopg and DATABASE_URL. Does not mutate data or resolve legacy
source provenance. Run only with private staging credentials.
"""
import argparse
import json
import os
import uuid


def audit(connection, textbook_id):
    with connection.transaction():
        with connection.cursor() as cur:
            cur.execute("set transaction read only")
            cur.execute("""
                select t.status,t.page_count,t.owner_uid,t.r2_key,
                       (select count(*) from source_library_staging.source_versions v
                        where v.textbook_id=t.id)
                from source_library_staging.textbooks t where t.id=%s
            """, (textbook_id,))
            record = cur.fetchone()
            if record is None:
                raise ValueError("Textbook not found")
            status, pages, owner, key, versions = record
            cur.execute("""
                select count(*), count(distinct chunk_index), min(chunk_index),
                       max(chunk_index), count(*) filter (where length(btrim(content))=0),
                       count(*) filter (where page_start<1 or page_end> %s
                                           or page_end<page_start)
                from source_library_staging.passages where textbook_id=%s
            """, (pages, textbook_id))
            total, distinct_count, first, last, blank, invalid = cur.fetchone()
            cur.execute("""
                select chunk_index,page_start
                from source_library_staging.passages
                where textbook_id=%s and
                      content_search @@ plainto_tsquery('english',%s)
                order by ts_rank(content_search,plainto_tsquery('english',%s)) desc
                limit 5
            """, (textbook_id, "airway", "airway"))
            hits = [{"chunk_index": i, "pdf_page": p} for i, p in cur.fetchall()]
    checks = {
        "ready": status == "ready",
        "owner_scoped_r2_key": key.startswith(str(owner) + "/"),
        "contiguous_chunks": total > 0 and distinct_count == total and first == 0 and last == total - 1,
        "valid_passages": blank == 0 and invalid == 0,
        "airway_search_returns_results": bool(hits),
        "source_provenance_recorded": versions > 0,
    }
    return {"textbook_id": str(textbook_id), "page_count": pages,
            "passage_count": total, "search_hits": hits, "checks": checks,
            "index_integrity_passed": all(v for k,v in checks.items()
                                          if k != "source_provenance_recorded"),
            "safe_to_reindex": checks["source_provenance_recorded"]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--textbook-id", type=uuid.UUID, required=True)
    args = parser.parse_args()
    import psycopg
    url = os.environ.get("DATABASE_URL")
    if not url:
        parser.error("DATABASE_URL is required")
    with psycopg.connect(url, options="-c search_path=source_library_staging,pg_catalog") as conn:
        result = audit(conn, args.textbook_id)
    print(json.dumps(result, indent=2))
    if not result["index_integrity_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
