"""Trusted, read-only Phase C bridge: indexed passages to v2 draft screening.

The caller owns authentication, database connection, and explicit model adapters.
No default model, network transport, database write, or publication is provided.
PDF page locations are not verified printed-page textbook citations.
"""
from build_question_evidence import build_evidence
from item_generation_screened_v2 import generate_and_screen


def generate_from_index(conn, owner_uid, topic, adapter, *, mode, domain, section,
                        objective, item_id, format="MC", textbook_id=None,
                        limit=8, known_stems=(), calculation=None,
                        embedding=None, neighbors=None, blind_reviewer=None,
                        generator_model_id=None, reviewer_model_id=None):
    if not isinstance(owner_uid, str) or not owner_uid.strip():
        raise ValueError("Authenticated source owner required")
    if not callable(adapter):
        raise ValueError("Explicit authenticated generator adapter required")
    if blind_reviewer is not None and (not callable(blind_reviewer)
                                      or not generator_model_id
                                      or not reviewer_model_id
                                      or generator_model_id == reviewer_model_id):
        raise ValueError("Independent blind reviewer and distinct model identities required")
    packet = build_evidence(conn, owner_uid, topic, textbook_id=textbook_id, limit=limit)
    if not packet["can_generate_grounded_questions"]:
        raise ValueError("No indexed textbook evidence found; generation blocked")
    evidence = packet["sources"]
    if not evidence or any(p.get("citation_verified") is not False for p in evidence):
        raise ValueError("Unexpected indexed evidence verification state")
    result = generate_and_screen(
        adapter, mode=mode, domain=domain, section=section,
        objective=objective, evidence=evidence, format=format, item_id=item_id,
        known_stems=known_stems, calculation=calculation, embedding=embedding,
        neighbors=neighbors, blind_reviewer=blind_reviewer,
        generator_model_id=generator_model_id, reviewer_model_id=reviewer_model_id)
    return {**result, "source_evidence": {
        "topic": packet["topic"],
        "passage_ids": [p["passage_id"] for p in evidence],
        "pdf_page_locations_only": True,
        "printed_page_citations_verified": False,
    }, "requires_human_review": True, "can_publish": False,
        "database_writes": False}
