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
from item_generation_checkpoint_store_v2 import fingerprint, load, record, complete, recover_completed


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
    if args.execute and env.get("AI_BLIND_REVIEW_OPT_IN") == "true" and not (args.confirm_paid_calls and env.get("AI_GENERATION_OPT_IN") == "true"):
        raise ValueError("Blind review requires explicit paid generation opt-in")
    if args.execute and env.get("AI_REWRITE_OPT_IN") == "true" and not (args.confirm_paid_calls and env.get("AI_GENERATION_OPT_IN") == "true"):
        raise ValueError("Rewrite requires explicit paid generation opt-in")
    if args.execute and env.get("AI_GENERATION_CHECKPOINTS_ENABLED") == "true" and not args.textbook_id:
        raise ValueError("Checkpointed generation requires an explicit textbook ID")
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
    # The resume key binds owner, textbook, request parameters, and indexed
    # evidence. Any evidence change invalidates the previous checkpoint.
    request_hash = fingerprint({"owner_uid": args.owner_uid, "topic": args.topic,
        "mode": args.mode, "domain": args.domain, "section": args.section,
        "objective": args.objective, "format": args.format, "item_id": args.item_id,
        "textbook_id": args.textbook_id, "section_id": args.section_id,
        "include_subsections": args.include_subsections, "page_start": args.page_start,
        "page_end": args.page_end, "limit": args.limit,
        "generator_model": env.get("AI_GENERATOR_MODEL", ""),
        "provider_endpoint": env.get("AI_PROVIDER_ENDPOINT", ""),
        "rewrite_enabled": env.get("AI_REWRITE_OPT_IN") == "true",
        "blind_review_enabled": env.get("AI_BLIND_REVIEW_OPT_IN") == "true",
        "reviewer_model": env.get("AI_REVIEWER_MODEL", "") if env.get("AI_BLIND_REVIEW_OPT_IN") == "true" else None})
    evidence_hash = fingerprint(evidence["sources"])
    if not args.execute:
        if (env.get("AI_GENERATION_CHECKPOINTS_ENABLED") == "true"
                and args.textbook_id):
            from item_generation_checkpoint_store_v2 import status as resume_status
            summary["resume"] = resume_status(
                conn, owner_uid=args.owner_uid, textbook_id=args.textbook_id,
                request_hash=request_hash, evidence_hash=evidence_hash)
        return summary
    checkpoint_enabled = env.get("AI_GENERATION_CHECKPOINTS_ENABLED") == "true"
    if checkpoint_enabled:
        recovered = recover_completed(
            conn, owner_uid=args.owner_uid, textbook_id=args.textbook_id,
            request_hash=request_hash, evidence_hash=evidence_hash)
        if recovered is not None:
            return recovered
    endpoint = env.get("AI_PROVIDER_ENDPOINT", "")
    host = urlsplit(endpoint).hostname
    if not host or host not in set(filter(None, env.get("AI_ALLOWED_HOSTS", "").split(","))):
        raise ValueError("Provider endpoint must match explicit host allowlist")
    relay_secret = env.get('STAGING_RECEIPT_SIGNING_SECRET', '')
    if not relay_secret:
        raise ValueError('Staging relay signing secret required')
    transport = make_transport(allowed_hosts=[host], timeout_seconds=60,
        relay_url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',
        relay_secret=relay_secret)
    adapter = make_adapter(endpoint=endpoint, api_key=env.get("AI_PROVIDER_API_KEY", ""),
                           model=env.get("AI_GENERATOR_MODEL", ""),
                           transport=transport, owner_opt_in=True, staging=True)
    reviewer_enabled = env.get("AI_BLIND_REVIEW_OPT_IN") == "true"
    reviewer_model_id = env.get("AI_REVIEWER_MODEL", "").strip()
    if reviewer_enabled:
        if not reviewer_model_id or reviewer_model_id == env.get("AI_GENERATOR_MODEL", "").strip():
            raise ValueError("Blind review requires a distinct configured model")
        reviewer_adapter = make_adapter(
            endpoint=endpoint, api_key=env.get("AI_PROVIDER_API_KEY", ""),
            model=reviewer_model_id, transport=transport,
            owner_opt_in=True, staging=True)
        def blind_reviewer(payload):
            return reviewer_adapter({**payload, "step": "blind_review",
                                     "blind": True, "rules_version": "2.0",
                                     "auto_publish": False})
    else:
        blind_reviewer = None
    checkpoint = (load(conn, owner_uid=args.owner_uid, textbook_id=args.textbook_id,
        request_hash=request_hash, evidence_hash=evidence_hash)
        if checkpoint_enabled else None)
    def checkpoint_writer(stage, value):
        record(conn, owner_uid=args.owner_uid, textbook_id=args.textbook_id,
            request_hash=request_hash, evidence_hash=evidence_hash,
            stage=stage, value=value)
    # A rewrite is an additional paid provider call. It is disabled by default
    # and requires a separate explicit staging opt-in.
    rewrite_enabled = env.get("AI_REWRITE_OPT_IN") == "true"
    def rewrite(request):
        return adapter({**request, "step": "rewrite",
                        "rules_version": "2.0", "auto_publish": False})
    result = generate_from_index(conn, args.owner_uid, args.topic, adapter,
                                 mode=args.mode, domain=args.domain,
                                 section=args.section, objective=args.objective,
                                 item_id=args.item_id, format=args.format,
                                 textbook_id=args.textbook_id, limit=args.limit,
                                 section_id=args.section_id,
                                 include_subsections=args.include_subsections,
                                 page_start=args.page_start, page_end=args.page_end,
                                 checkpoint=checkpoint,
                                 generator_model_id=env["AI_GENERATOR_MODEL"],
                                 on_checkpoint=checkpoint_writer if checkpoint_enabled else None,
                                 evidence_packet=evidence,
                                 rewrite=rewrite if rewrite_enabled else None,
                                 blind_reviewer=blind_reviewer,
                                 reviewer_model_id=reviewer_model_id if reviewer_enabled else None)
    save_payload = {"textbook_id": args.textbook_id, "topic": args.topic,
                    "mode": args.mode, "format": args.format,
                    "domain": args.domain, "section": args.section,
                    "objective": args.objective, "provider": host,
                    "model": env["AI_GENERATOR_MODEL"], "question": result["item"],
                    "screening": result["screening"] or {"next_state": result["next_state"],
                        "generator_issues": result["generator_issues"]},
                    "evidence": [{"passage_id": p["passage_id"],
                                  "textbook_id": p["textbook_id"]}
                                 for p in evidence["sources"]]}
    response = {**summary, "dry_run": False, "save_payload": save_payload, "item_id": result["item_id"],
            "next_state": result["next_state"],
            "item": result["item"], "requires_human_review": True,
            "source_evidence": result["source_evidence"],
            "generator_issues": result["generator_issues"],
            "screening": result["screening"]}
    if checkpoint_enabled:
        complete(conn, owner_uid=args.owner_uid, textbook_id=args.textbook_id,
                 request_hash=request_hash, evidence_hash=evidence_hash,
                 result=response)
    return response



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
