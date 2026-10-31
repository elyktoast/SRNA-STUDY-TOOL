#!/usr/bin/env python3
"""Read-only staging retrieval benchmark.

Fixture JSON contains queries, expected passage IDs, and optional textbook ID.
Requires private DATABASE_URL and explicit owner UID; no source text is logged.
"""
import argparse
import json
import os
from pathlib import Path

from search_passages import search, UUID_RE
from source_retrieval_benchmark_v2 import evaluate


def run(conn, *, owner_uid, fixtures, limit=10, min_recall_at_k=0.8):
    if not isinstance(owner_uid, str) or not UUID_RE.fullmatch(owner_uid):
        raise ValueError("Valid owner UUID required")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Limit must be 1..50")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("Benchmark fixtures required")
    for fixture in fixtures:
        if not isinstance(fixture, dict):
            raise ValueError("Invalid benchmark fixture")
        textbook_id = fixture.get("textbook_id")
        if textbook_id is not None and (
                not isinstance(textbook_id, str) or not UUID_RE.fullmatch(textbook_id)):
            raise ValueError("Invalid textbook UUID")
    # Search each case independently so the textbook filter cannot leak across cases.
    indexed = iter(fixtures)
    def query_search(query):
        case = next(indexed)
        if query != case["query"]:
            raise ValueError("Benchmark query mismatch")
        rows = search(conn, query, owner_uid, limit=limit,
                      textbook_id=case.get("textbook_id"))
        return [{"passage_id": row["passage_id"],
                 "pdf_page_start": row["pdf_page_start"],
                 "pdf_page_end": row["pdf_page_end"]} for row in rows]
    return evaluate(query_search, fixtures, min_recall_at_k=min_recall_at_k)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--min-recall", type=float, default=0.8)
    args = parser.parse_args()
    url = os.environ.get("DATABASE_URL")
    if not url:
        parser.error("Private staging DATABASE_URL required")
    fixtures = json.loads(args.fixtures.read_text(encoding="utf-8"))
    import psycopg
    with psycopg.connect(url, autocommit=False) as conn:
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("SET TRANSACTION READ ONLY")
            report = run(conn, owner_uid=args.owner_uid, fixtures=fixtures,
                         limit=args.limit, min_recall_at_k=args.min_recall)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
