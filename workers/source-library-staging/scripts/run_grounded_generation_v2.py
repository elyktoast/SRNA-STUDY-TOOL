#!/usr/bin/env python3
"""Explicitly opted-in staging CLI for indexed, screened question drafts.

Runs on a trusted backend, never in the browser. Defaults to a no-cost preflight.
Does not persist drafts, print source excerpts, or approve publication.
"""
import argparse
import json
import os
import re
from urllib.parse import urlsplit

from build_question_evidence import build_evidence
from item_ai_https_transport_v2 import make_transport
from item_ai_provider_v2 import make_adapter
from item_grounded_pipeline_v2 import generate_from_index


def execute(conn, args, environ=None):
    env = os.environ if environ is None else environ
    if env.get("STAGING_ONLY") != "true":
        raise ValueError("Staging-only execution required")
    if (args.mode not in ("NCE", "SEE") or args.domain not in ("I", "II", "III", "IV")
            or not isinstance(args.section, str) or not re.fullmatch(r"[A-Z]", args.section)
            or not isinstance(args.objective, str)
            or not re.fullmatch(r"(I|II|III|IV)\.[A-Z]\.\d+(?:\.\d+)*", args.objective)
            or args.objective.split(".")[:2] != [args.domain, args.section]
            or args.format not in ("MC", "MS", "SA", "DD", "HS")):
        raise ValueError("Invalid NCE/SEE blueprint classification")
    if args.execute and (env.get("AI_GENERATION_OPT_IN") != "true" or not args.confirm_paid_calls):
        raise ValueError("Paid model calls require explicit opt-in and confirmation")
    evidence = build_evidence(conn, args.owner_uid, args.topic,
                              textbook_id=args.textbook_id, limit=args.limit,
                              section_id=args.section_id,
                              include_subsections=args.include_subsections,
                              page_start=args.page_start, page_end=args.page_end)
    if not evidence["can_generate_grounded_questions"]:
        raise ValueError("No indexed textbook evidence found")
    summary = {"topic": evidence["topic"], "passage_count": evidence["evidence_count"],
               "mode": args.mode, "format": args.format,
               "dry_run": not args.execute, "can_publish": False,
               "database_writes": False}
    if not args.execute:
        return summary
    endpoint = env.get("AI_PROVIDER_ENDPOINT", "")
    host = urlsplit(endpoint).hostname
    if not host or host not in set(filter(None, env.get("AI_ALLOWED_HOSTS", "").split(","))):
        raise ValueError("Provider endpoint must match explicit host allowlist")
    transport = make_transport(allowed_hosts=[host])
    adapter = make_adapter(endpoint=endpoint, api_key=env.get("AI_PROVIDER_API_KEY", ""),
                           model=env.get("AI_GENERATOR_MODEL", ""),
                           transport=transport, owner_opt_in=True, staging=True)
    result = generate_from_index(conn, args.owner_uid, args.topic, adapter,
                                 mode=args.mode, domain=args.domain,
                                 section=args.section, objective=args.objective,
                                 item_id=args.item_id, format=args.format,
                                 textbook_id=args.textbook_id, limit=args.limit,
                                 section_id=args.section_id,
                                 include_subsections=args.include_subsections,
                                 page_start=args.page_start, page_end=args.page_end)
    return {**summary, "dry_run": False, "item_id": result["item_id"],
            "next_state": result["next_state"],
            "source_evidence": result["source_evidence"],
            "generator_issues": result["generator_issues"],
            "screening": result["screening"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic")
    parser.add_argument("--owner-uid", required=True)
    parser.add_argument("--mode", choices=("NCE", "SEE"), required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--section", required=True)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--format", choices=("MC", "MS", "SA", "DD", "HS"), default="MC")
    parser.add_argument("--item-id", required=True)
    parser.add_argument("--textbook-id")
    parser.add_argument("--section-id")
    parser.add_argument("--include-subsections", action="store_true")
    parser.add_argument("--page-start", type=int)
    parser.add_argument("--page-end", type=int)
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--confirm-paid-calls", action="store_true")
    args = parser.parse_args()
    if not os.environ.get("DATABASE_URL"):
        parser.error("DATABASE_URL required")
    import psycopg
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        output = execute(conn, args)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
