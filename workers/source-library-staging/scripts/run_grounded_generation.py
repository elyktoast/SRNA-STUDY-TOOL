#!/usr/bin/env python3
"""Operator-only staging runner: search indexed evidence and optionally generate drafts.

Dry-run is the default. It prints metadata only, never copyrighted passages,
credentials or question content. Generated drafts remain in memory; no database writes.
"""
import argparse
import json
import os

from prepare_grounded_generation import prepare
from generate_grounded_drafts import generate_drafts


def run(conn, owner_uid, topic, *, textbook_id=None, count=5, generate=False,
        endpoint=None, jwt=None, apikey=None, transport=None):
    if not generate:
        request = prepare(conn, owner_uid, topic, textbook_id=textbook_id, count=count)
        return {"mode": "dry-run", "ready": True,
                "passage_count": len(request["evidence"]["passage_ids"]),
                "question_count_requested": request["count"],
                "citation_verified": False, "database_writes": False}
    result = generate_drafts(conn, owner_uid, topic, textbook_id=textbook_id,
                             count=count, endpoint=endpoint, jwt=jwt,
                             apikey=apikey, transport=transport)
    return {"mode": "generation", "draft_count": result["count"],
            "exact_excerpt_matches": sum(d["sourceExcerptMatch"] == "exact" for d in result["drafts"]),
            "unmatched_excerpts": sum(d["sourceExcerptMatch"] == "unmatched" for d in result["drafts"]),
            "auto_approved": False, "database_writes": False,
            "drafts": result["drafts"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic")
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--textbook-id")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--generate", action="store_true",
                        help="Explicitly call AI generator (may incur API costs)")
    parser.add_argument("--output", help="Private local JSON path for drafts, required with --generate")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        parser.error("DATABASE_URL required")
    if args.generate and not args.output:
        parser.error("--output required with --generate")
    if args.output and not args.generate:
        parser.error("--output only applies with --generate")
    if args.generate and os.path.exists(args.output):
        parser.error("Output already exists; refusing to overwrite")
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        result = run(conn, args.owner_uid, args.topic, textbook_id=args.textbook_id,
                     count=args.count, generate=args.generate,
                     endpoint=os.environ.get("QUESTION_GENERATOR_ENDPOINT"),
                     jwt=os.environ.get("QUESTION_GENERATOR_JWT"),
                     apikey=os.environ.get("QUESTION_GENERATOR_ANON_KEY"))
    if args.generate:
        # Exclusive creation and owner-only permissions. Do not upload to public CI artifacts.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(result.pop("drafts"), stream, ensure_ascii=False, indent=2)
        result["drafts_saved_locally"] = True
    print(json.dumps(result))


if __name__ == "__main__":
    main()
