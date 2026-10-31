#!/usr/bin/env python3
"""Prepare a source-grounded request for the existing generate-questions endpoint.

Private backend only. Never log textbook excerpts or send this payload to a browser
without authorization. This does not call an AI provider or approve generated drafts.
"""
import argparse
import json
import os

from build_question_evidence import build_evidence


def prepare(conn, owner_uid, topic, *, textbook_id=None, count=5, limit=8):
    if type(count) is not int or not 1 <= count <= 20:
        raise ValueError("Question count must be 1..20")
    evidence = build_evidence(conn, owner_uid, topic, textbook_id=textbook_id, limit=limit)
    if not evidence["can_generate_grounded_questions"]:
        raise ValueError("No indexed textbook evidence found; generation blocked")
    sources = evidence["sources"]
    material = "\n\n".join(
        f"[SOURCE {i+1} | passage_id={s['passage_id']} | textbook_id={s['textbook_id']} | "
        f"PDF pages {s['pdf_page_start']}-{s['pdf_page_end']}]\n{s['excerpt']}"
        for i, s in enumerate(sources)
    )
    if len(material) > 100000:
        raise ValueError("Evidence exceeds generator material limit")
    return {
        "material": material,
        "sourceName": "Indexed Source Library (staging)",
        "citation": "Physical PDF page references only; printed-page citations unverified",
        "count": count,
        "evidence": {
            "passage_ids": [s["passage_id"] for s in sources],
            "citation_verified": False,
            "requires_human_review": True,
            "note": "Generated questions must be checked against the identified passages before approval.",
        },
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("topic")
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--textbook-id")
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        parser.error("DATABASE_URL required")
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = prepare(conn, args.owner_uid, args.topic, textbook_id=args.textbook_id, count=args.count)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
