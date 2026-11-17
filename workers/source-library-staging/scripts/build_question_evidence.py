#!/usr/bin/env python3
"""Read-only textbook evidence retrieval for question generation and verification.

Returns short, source-linked excerpts; PDF page numbers are NOT printed-page citations.
Run only on trusted backend infrastructure. Never expose DATABASE_URL to browsers.
"""
import argparse
import json
import os
import re

from search_passages import search, UUID_RE
from item_source_scope_v2 import source_scope

TEACHING_PREFIX = re.compile(
    r"^(?:explain|describe|discuss|identify|define|summarize|evaluate|analy[sz]e|"
    r"compare(?:\s+and\s+contrast)?|contrast|recognize|understand)\s+"
    r"(?:the\s+)?(?:relationship\s+between\s+)?", re.I)


def topic_search_query(topic):
    """Remove instructional wording without dropping clinical search terms."""
    if not isinstance(topic, str) or not topic.strip() or len(topic) > 500:
        raise ValueError("Topic must be 1..500 characters")
    # Teaching verbs need not occur in a textbook's explanation. Keep the
    # complete clinical subject/relation and every scope predicate unchanged.
    return TEACHING_PREFIX.sub("", topic.strip(), count=1).strip() or topic.strip()


def build_evidence(conn, owner_uid, topic, *, textbook_id=None, limit=8,
                   section_id=None, include_subsections=False,
                   page_start=None, page_end=None, textbook_ids=None, balance_books=False):
    query = topic_search_query(topic)
    books = source_scope(textbook_id, textbook_ids)
    if balance_books:
        if textbook_id is not None or textbook_ids is not None:
            raise ValueError('Balanced library discovery requires no explicit book selection')
        if not isinstance(owner_uid, str) or not UUID_RE.fullmatch(owner_uid):
            raise ValueError('Invalid owner UUID')
        with conn.cursor() as cur:
            cur.execute("""select id::text from source_library_staging.textbooks
              where owner_uid=%s::uuid and status='ready' order by id limit 9""", (owner_uid,))
            books = [r[0] for r in cur.fetchall()]
        if len(books) > 8:
            raise ValueError('Select at most eight textbooks for combined evidence')
    if balance_books or (books is not None and len(books) > 1):
        if any(value is not None for value in (section_id, page_start, page_end)) or include_subsections:
            raise ValueError('Physical page and section filters require a single textbook')
        if type(limit) is not int or not (1 if balance_books else len(books)) <= limit <= 50:
            raise ValueError('Passage limit must cover every selected textbook, up to 50')
        # Fair, bounded interleaving prevents one large book monopolizing the
        # packet. Each search independently enforces ownership and ready state.
        groups = [search(conn, query, owner_uid, limit=limit, textbook_id=book)
                  for book in books]
        if balance_books:
            groups.sort(key=lambda group: -group[0].get('rank',0) if group else 0)
        rows = [group[index] for index in range(limit) for group in groups
                if index < len(group)][:limit]
        if textbook_id is not None and rows and not any(row['textbook_id'] == textbook_id for row in rows):
            raise ValueError('No indexed textbook evidence found in primary textbook')
    else:
        rows = search(conn, query, owner_uid, limit=limit, textbook_id=textbook_id,
                      section_id=section_id, include_subsections=include_subsections,
                      page_start=page_start, page_end=page_end)
    sources = []
    for row in rows:
        sources.append({
            "passage_id": row["passage_id"],
            "textbook_id": row["textbook_id"],
            "filename": row["filename"],
            "pdf_page_start": row["pdf_page_start"],
            "pdf_page_end": row["pdf_page_end"],
            "excerpt": row["excerpt"],
            "section_heading": row.get("section_heading"),
            "edition": row.get("edition"),
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
