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


def _call_with_bounded_rate_wait(adapter, payload):
    """Retry once only after an explicit 429 with a bounded server delay."""
    import time
    from item_ai_https_transport_v2 import TransportError
    try:
        return adapter(payload)
    except TransportError as exc:
        delay = exc.retry_after_seconds
        if exc.rule != "PROVIDER_RATE_LIMIT" or type(delay) is not int or not 1 <= delay <= 60:
            raise
        # The provider can increase its token estimate between identical attempts.
        # Let one full TPM window drain, still with exactly one bounded retry.
        time.sleep(60)
        return adapter(payload)


def execute(conn, args, environ=None, *, semantic_lookup=None):
    env = os.environ if environ is None else environ
    if semantic_lookup is not None and not callable(semantic_lookup):
        raise ValueError("Trusted semantic lookup callback required")
    if env.get("STAGING_ONLY") != "true":
        raise ValueError("Staging-only execution required")
    if (args.mode not in ("NCE", "SEE") or args.domain not in ("I", "II", "III", "IV")
            or not isinstance(args.section, str) or not re.fullmatch(r"[A-Z]", args.section)
            or not isinstance(args.objective, str)
            or not re.fullmatch(r"(I|II|III|IV)\.[A-Z]\.\d+(?:\.\d+)*", args.objective)
            or args.objective.split(".")[:2] != [args.domain, args.section]
            or args.format not in ("MC", "MS", "SA", "DD", "HS")):
        raise ValueError("Invalid NCE/SEE blueprint classification")
    from item_board_quality_v2 import classification
    classification(args.domain, args.section, args.objective)
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
    summary = {"authoring_contract": "2026-11-10-v18", "topic": evidence["topic"], "passage_count": evidence["evidence_count"],
               "mode": args.mode, "format": args.format,
               "dry_run": not args.execute, "can_publish": False,
               "database_writes": False}
    # Safe, no-cost review readiness: never imply that a configured provider
    # or a requested flag is an independently completed review.
    generator_id = env.get("AI_GENERATOR_MODEL", "").strip()
    reviewer_id = env.get("AI_REVIEWER_MODEL", "").strip()
    blind_requested = env.get("AI_BLIND_REVIEW_OPT_IN") == "true"
    option_requested = env.get("AI_OPTION_REVIEW_OPT_IN") == "true"
    rewrite_requested = env.get("AI_REWRITE_OPT_IN") == "true"
    explanation_requested = env.get("AI_EXPLANATION_REVIEW_OPT_IN") == "true"
    quality_requested = blind_requested and explanation_requested and args.format in ("MC", "MS")
    editorial_model = env.get("AI_EDITORIAL_REVIEWER_MODEL", "").strip()
    authoring_provider = env.get("AI_AUTHORING_PROVIDER", "groq")
    if authoring_provider not in ("groq", "cloudflare"):
        raise ValueError("Invalid provider delivery configuration")
    delivery_model = env.get("AI_CLOUDFLARE_MODEL", "") if authoring_provider == "cloudflare" else generator_id
    if authoring_provider == "cloudflare" and delivery_model != "@cf/" + generator_id:
        raise ValueError("Cloudflare provider model must match the generator identity")
    summary["authoring_provider"] = authoring_provider
    summary["authoring_delivery_model"] = delivery_model
    summary["quality_contract"] = "2026-11-10-v2" if quality_requested else None
    summary["review_readiness"] = {
        "board_quality_review": "configured" if quality_requested and generator_id and reviewer_id and generator_id != reviewer_id and editorial_model and editorial_model != generator_id else "unavailable" if quality_requested else "disabled",
        "rewrite": "configured" if rewrite_requested and generator_id else
                   "missing_generator_model" if rewrite_requested else "disabled",
        "blind_review": (
            "configured" if blind_requested and reviewer_id and generator_id
            and reviewer_id != generator_id else
            "missing_reviewer_model" if blind_requested and not reviewer_id else
            "missing_generator_model" if blind_requested and not generator_id else
            "reviewer_must_differ" if blind_requested else "disabled"),
        "independent_option_review": "configured" if option_requested and generator_id and reviewer_id and generator_id != reviewer_id else "unavailable" if option_requested else "disabled",
        "explanation_review": "configured" if explanation_requested and generator_id and reviewer_id and generator_id != reviewer_id else "unavailable" if explanation_requested else "disabled",
        "independent_review_completed": False,
        "clinical_review_required": True,
    }
    # Configuration is not a network health check; preflight must never imply
    # a provider was contacted or a draft was stored.
    endpoint = env.get("AI_PROVIDER_ENDPOINT", "")
    provider_host = urlsplit(endpoint).hostname
    allowed_hosts = set(filter(None, env.get("AI_ALLOWED_HOSTS", "").split(",")))
    summary["execution_readiness"] = {
        "indexed_evidence_found": True,
        "provider_endpoint_allowlisted": bool(provider_host and provider_host in allowed_hosts),
        "generator_model_configured": bool(generator_id),
        "provider_api_key_configured": bool(env.get("AI_PROVIDER_API_KEY")),
        "relay_secret_configured": bool(env.get("STAGING_RECEIPT_SIGNING_SECRET")),
        "provider_connectivity_checked": False,
        "draft_persistence": "not_performed_by_cli",
    }
    if args.execute and blind_requested and summary["review_readiness"]["blind_review"] != "configured":
        raise ValueError("Blind review requires distinct configured generator and reviewer models")
    if args.execute and explanation_requested and summary["review_readiness"]["explanation_review"] != "configured":
        raise ValueError("Explanatory review requires distinct configured models")
    if args.execute and quality_requested and summary["review_readiness"]["board_quality_review"] != "configured":
        raise ValueError("Editorial review requires a distinct configured model")
    if args.execute and rewrite_requested and not generator_id:
        raise ValueError("Rewrite requires a configured generator model")
    # The resume key binds owner, textbook, request parameters, and indexed
    # evidence. Any evidence change invalidates the previous checkpoint.
    request_hash = fingerprint({"authoring_contract": "2026-11-10-v18", "owner_uid": args.owner_uid, "topic": args.topic,
        "mode": args.mode, "domain": args.domain, "section": args.section,
        "objective": args.objective, "format": args.format, "item_id": args.item_id,
        "textbook_id": args.textbook_id, "section_id": args.section_id,
        "include_subsections": args.include_subsections, "page_start": args.page_start,
        "page_end": args.page_end, "limit": args.limit,
        "generator_model": env.get("AI_GENERATOR_MODEL", ""),
        "authoring_provider": authoring_provider, "authoring_delivery_model": delivery_model,
        "provider_endpoint": env.get("AI_PROVIDER_ENDPOINT", ""),
        "rewrite_enabled": env.get("AI_REWRITE_OPT_IN") == "true",
        "blind_review_enabled": env.get("AI_BLIND_REVIEW_OPT_IN") == "true",
        "explanation_review_enabled": explanation_requested,
        "board_quality_contract": "2026-11-10-v2" if quality_requested else None,
        "editorial_reviewer_model": editorial_model if quality_requested else None,
        "explanation_reviewer_model": reviewer_id if explanation_requested else None,
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
            return {**recovered, "_checkpoint_key": {"textbook_id": args.textbook_id,
                "request_hash": request_hash, "evidence_hash": evidence_hash}}
    endpoint = env.get("AI_PROVIDER_ENDPOINT", "")
    host = urlsplit(endpoint).hostname
    if not host or host not in set(filter(None, env.get("AI_ALLOWED_HOSTS", "").split(","))):
        raise ValueError("Provider endpoint must match explicit host allowlist")
    relay_secret = env.get('STAGING_RECEIPT_SIGNING_SECRET', '')
    if not relay_secret:
        raise ValueError('Staging relay signing secret required')
    transport = make_transport(allowed_hosts=[host], timeout_seconds=50,
        relay_url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/internal/groq-relay',
        relay_secret=relay_secret)
    adapter = make_adapter(endpoint=endpoint, api_key=env.get("AI_PROVIDER_API_KEY", ""),
                           model=env.get("AI_GENERATOR_MODEL", ""),
                           transport=transport, owner_opt_in=True, staging=True)
    reviewer_enabled = env.get("AI_BLIND_REVIEW_OPT_IN") == "true" or option_requested or explanation_requested
    reviewer_model_id = env.get("AI_REVIEWER_MODEL", "").strip()
    if reviewer_enabled:
        if not reviewer_model_id or reviewer_model_id == env.get("AI_GENERATOR_MODEL", "").strip():
            raise ValueError("Blind review requires a distinct configured model")
        reviewer_adapter = make_adapter(
            endpoint=endpoint, api_key=env.get("AI_PROVIDER_API_KEY", ""),
            model=reviewer_model_id, transport=transport,
            owner_opt_in=True, staging=True)
        def blind_reviewer(payload):
            return _call_with_bounded_rate_wait(reviewer_adapter, {**payload, "step": "blind_review",
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
    def option_reviewer(payload):
        response = _call_with_bounded_rate_wait(reviewer_adapter, {**payload, "step": "option_review", "blind": True,
                                     "rules_version": "2.0", "auto_publish": False})
        if set(response) != {"judgments"} or not isinstance(response["judgments"], list):
            raise ValueError("Independent option reviewer returned invalid judgments")
        judgments = response["judgments"]
        if any(not isinstance(j, dict) or type(j.get("source_conflict_found")) is not bool for j in judgments):
            raise ValueError("Independent source conflict state required")
        # Adapt the unambiguous provider field to the existing evaluator contract.
        return [{**j, "contradiction_found": j["source_conflict_found"]} for j in judgments]
    def explanation_review(item):
        from item_explanation_review_v2 import review
        report = review(item, evidence["sources"],
                        lambda payload: _call_with_bounded_rate_wait(reviewer_adapter, payload), batch_size=6)
        return {**report, "generator_model_id": generator_id, "reviewer_model_id": reviewer_model_id}
    def quality_review(item):
        from item_board_quality_v2 import editorial, options_only
        editorial_adapter = make_adapter(endpoint=endpoint, api_key=env.get("AI_PROVIDER_API_KEY", ""),
            model=editorial_model, transport=transport, owner_opt_in=True, staging=True)
        reports = {"editorial_quality": editorial(item, lambda payload: _call_with_bounded_rate_wait(editorial_adapter, payload),
                counterfactual_reviewer=blind_reviewer, selected_topic=args.topic),
                   "options_only": options_only(item, lambda payload: _call_with_bounded_rate_wait(reviewer_adapter, payload))}
        return {name: {**report, "generator_model_id": generator_id,
                      "reviewer_model_id": editorial_model if name == "editorial_quality" else reviewer_model_id}
                for name, report in reports.items()}
    # A rewrite is an additional paid provider call. It is disabled by default
    # and requires a separate explicit staging opt-in.
    rewrite_enabled = env.get("AI_REWRITE_OPT_IN") == "true"
    def rewrite(request):
        import copy
        from item_generation_runner_v2 import _hydrate_indexed_citations
        references = {c.get("passage_id") for c in request.get("item", {}).get("evidence", [])
                      if isinstance(c, dict)}
        for entry in request.get("item", {}).get("distractor_evidence", {}).values():
            if isinstance(entry, dict) and isinstance(entry.get("passage_ids"), list):
                references.update(pid for pid in entry["passage_ids"] if isinstance(pid, str))
        trusted = [p for p in evidence["sources"] if p["passage_id"] in references]
        compact = copy.deepcopy(request)
        for citation in compact.get("item", {}).get("evidence", []):
            if isinstance(citation, dict):
                citation.pop("excerpt", None)
        payload = {**compact, "trusted_evidence": trusted, "step": "rewrite",
                   "rules_version": "2.0", "auto_publish": False}
        candidate = _call_with_bounded_rate_wait(adapter, payload)
        return _hydrate_indexed_citations(candidate, evidence["sources"])
    def author(payload):
        value = _call_with_bounded_rate_wait(adapter, payload)
        if authoring_provider == "cloudflare" and payload.get("step") == "concept_card" and payload.get("format") == "MC":
            concept = value.get("concept_card") if isinstance(value, dict) and set(value) == {"concept_card"} else value
            if not isinstance(concept, dict) or not isinstance(concept.get("choice_plan"), dict):
                raise ValueError("Concept card choice plan incomplete")
        return value
    result = generate_from_index(conn, args.owner_uid, args.topic, author,
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
                                 review_repair=rewrite if rewrite_enabled else None,
                                 blind_reviewer=blind_reviewer if env.get("AI_BLIND_REVIEW_OPT_IN") == "true" else None,
                                 reviewer_model_id=reviewer_model_id if reviewer_enabled else None,
                                 semantic_lookup=semantic_lookup,
                                 option_reviewer=option_reviewer if option_requested else None,
                                 option_reviewer_model_id=reviewer_model_id if option_requested else None,
                                 explanation_review=explanation_review if explanation_requested else None,
                                 quality_review=quality_review if quality_requested else None)
    from item_board_quality_v2 import stamp_checks
    result["item"] = stamp_checks(result["item"], result["screening"])
    save_payload = {"textbook_id": args.textbook_id, "topic": args.topic,
                    "mode": args.mode, "format": args.format,
                    "domain": args.domain, "section": args.section,
                    "objective": args.objective, "provider": "api.cloudflare.com" if authoring_provider == "cloudflare" else host,
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
    if checkpoint_enabled:
        response["_checkpoint_key"] = {"textbook_id": args.textbook_id,
            "request_hash": request_hash, "evidence_hash": evidence_hash}
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
