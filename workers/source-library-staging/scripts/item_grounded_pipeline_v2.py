"""Trusted, read-only Phase C bridge: indexed passages to v2 draft screening.

The caller owns authentication, database connection, and explicit model adapters.
No default model, network transport, database write, or publication is provided.
PDF page locations are not verified printed-page textbook citations.
"""
from build_question_evidence import build_evidence
from item_generation_screened_v2 import generate_and_screen


def generate_from_index(conn, owner_uid, topic, adapter, *, mode, domain, section,
                        objective, item_id, format="MC", textbook_id=None,
                        limit=8, section_id=None, include_subsections=False,
                        page_start=None, page_end=None, known_stems=(), calculation=None,
                        embedding=None, neighbors=None, blind_reviewer=None,
                        generator_model_id=None, reviewer_model_id=None,
                        checkpoint=None, on_checkpoint=None, evidence_packet=None,
                        rewrite=None, semantic_lookup=None, review_repair=None,
                        option_reviewer=None, option_reviewer_model_id=None):
    if not isinstance(owner_uid, str) or not owner_uid.strip():
        raise ValueError("Authenticated source owner required")
    if not callable(adapter):
        raise ValueError("Explicit authenticated generator adapter required")
    if blind_reviewer is not None and (not callable(blind_reviewer)
                                      or not generator_model_id
                                      or not reviewer_model_id
                                      or generator_model_id == reviewer_model_id):
        raise ValueError("Independent blind reviewer and distinct model identities required")
    if review_repair is not None and not callable(review_repair):
        raise ValueError("Explicit authenticated review repair adapter required")
    if option_reviewer is not None and (
            not callable(option_reviewer) or not isinstance(generator_model_id, str)
            or not generator_model_id.strip()
            or not isinstance(option_reviewer_model_id, str)
            or not option_reviewer_model_id.strip()
            or generator_model_id.strip() == option_reviewer_model_id.strip()):
        raise ValueError("Explicit independent option reviewer and distinct model identities required")
    packet = evidence_packet if evidence_packet is not None else build_evidence(
        conn, owner_uid, topic, textbook_id=textbook_id, limit=limit,
        section_id=section_id, include_subsections=include_subsections,
        page_start=page_start, page_end=page_end)
    if not isinstance(packet, dict):
        raise ValueError("Invalid indexed evidence packet")
    if not packet["can_generate_grounded_questions"]:
        raise ValueError("No indexed textbook evidence found; generation blocked")
    evidence = packet["sources"]
    if (not isinstance(evidence, list) or not evidence
            or any(not isinstance(p, dict)
                   or not all(isinstance(p.get(k), str) and p[k].strip()
                              for k in ("passage_id", "textbook_id", "excerpt"))
                   or type(p.get("pdf_page_start")) is not int
                   or p["pdf_page_start"] < 1
                   or type(p.get("pdf_page_end")) is not int
                   or p["pdf_page_end"] < p["pdf_page_start"]
                   or p.get("citation_verified") is not False
                   for p in evidence)
            or len({p["passage_id"] for p in evidence}) != len(evidence)):
        raise ValueError("Invalid or unverified indexed evidence; generation blocked")
    result = generate_and_screen(
        adapter, mode=mode, domain=domain, section=section,
        objective=objective, evidence=evidence, format=format, item_id=item_id,
        known_stems=known_stems, calculation=calculation, embedding=embedding,
        neighbors=neighbors, blind_reviewer=blind_reviewer,
        generator_model_id=generator_model_id, reviewer_model_id=reviewer_model_id,
        checkpoint=checkpoint, on_checkpoint=on_checkpoint,
        rewrite=rewrite, semantic_lookup=semantic_lookup,
        review_repair=review_repair, topic=topic)
    # Independent retrieval is diagnostic only: finding a passage is not proof
    # that it supports the key or refutes an alternative.
    option_audit = None
    if textbook_id and format in ("MC", "MS") and isinstance(result.get("item"), dict):
        try:
            from item_option_retrieval_audit_v2 import audit
            option_audit = audit(conn, owner_uid, result["item"], textbook_id=textbook_id, context_query=topic, limit=2)
        except (ValueError, KeyError, TypeError, RuntimeError):
            option_audit = {"all_options_searched": False,
                            "clinical_verification_complete": False,
                            "can_publish": False,
                            "error": "option_retrieval_unavailable"}
    option_adjudication = None
    if (option_reviewer is not None and format in ("MC", "MS")
            and isinstance(result.get("item"), dict) and isinstance(option_audit, dict)
            and not result.get("generator_issues")
            and result.get("screening", {}).get("stages", {}).get("schema", {}).get("status") == "pass"):
        from item_option_adjudication_handoff_v2 import run as review_options
        from search_passages import search
        passages = {}
        try:
            for entry in option_audit.get("option_audits", []):
                if entry.get("search_status") != "matches_found":
                    continue
                for query in entry.get("search_queries") or [entry["search_query"]]:
                    for passage in search(conn, query, owner_uid, limit=5, textbook_id=textbook_id):
                        passages[passage["passage_id"]] = passage
        except Exception:
            passages = {}
        option_adjudication = review_options(
            result["item"], option_audit, option_reviewer,
            source_passages=list(passages.values()),
            generator_model_id=generator_model_id,
            reviewer_model_id=option_reviewer_model_id, require_quotes=True)
    if format in ("MC", "MS"):
        from item_option_audit_screening_v2 import attach
        result = attach(result, option_audit, option_adjudication)
    return {**result, "independent_option_retrieval": option_audit,
            "independent_option_adjudication": option_adjudication, "source_evidence": {
        "topic": packet["topic"],
        "passage_ids": [p["passage_id"] for p in evidence],
        "pdf_page_locations_only": True,
        "printed_page_citations_verified": False,
    }, "requires_human_review": True, "can_publish": False,
        "database_writes": False}
