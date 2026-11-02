#!/usr/bin/env python3
"""Read-only textbook evidence retrieval for question generation and verification.

Returns short, source-linked excerpts; PDF page numbers are NOT printed-page citations.
Run only on trusted backend infrastructure. Never expose DATABASE_URL to browsers.
"""
import argparse
import json
import os

from search_passages import search


def build_evidence(conn, owner_uid, topic, *, textbook_id=None, limit=8):
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 500:
        raise ValueError("Topic must be 1..500 characters")
    rows = search(conn, topic.strip(), owner_uid, limit=limit, textbook_id=textbook_id)
    sources = []
    for row in rows:
        sources.append({
            "passage_id": row["passage_id"],
            "textbook_id": row["textbook_id"],
            "filename": row["filename"],
            "pdf_page_start": row["pdf_page_start"],
            "pdf_page_end": row["pdf_page_end"],
            "excerpt": row["excerpt"],
            "citation_verified": False,
            "citation_type": "physical_pdf_page_1_based",
        })
    return {
        "topic": topic.strip(),
        "evidence_count": len(sources),
        "can_generate_grounded_questions": bool(sources),
        "sources": sources,
        "instructions": (
            "Use only supplied source excerpts as evidence. For each proposed answer, "
            "explain which passage_id supports it. If evidence is insufficient, flag "
            "the question for review instead of inventing an answer. PDF page numbers "
            "are location references, not verified printed textbook citations."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("topic")
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--textbook-id")
    parser.add_argument("--limit", type=int, default=8)
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        parser.error("DATABASE_URL required")
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = build_evidence(conn, args.owner_uid, args.topic,
                                textbook_id=args.textbook_id, limit=args.limit)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
