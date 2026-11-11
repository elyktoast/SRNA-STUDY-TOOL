"""Private lecture-text planning pipeline backed by indexed textbook retrieval.

Read-only. Never sends lecture or textbook material to public services.
"""
from lecture_concept_extraction import extract
from lecture_question_plan import plan
from build_question_evidence import build_evidence


def prepare(conn, owner_uid, lecture_text, *, textbook_id=None, count=20,
            max_concepts=30, passage_limit=6):
    extracted = extract(lecture_text, max_concepts=max_concepts)
    concepts = extracted["concepts"]
    evidence = {}
    for topic in concepts:
        result = build_evidence(conn, owner_uid, topic["title"],
                                textbook_id=textbook_id, limit=passage_limit)
        evidence[topic["title"]] = result["sources"]
    planned = plan(concepts, evidence, count=count) if concepts else {
        "requested": count, "planned": 0, "topics": [],
        "missing_textbook_support": [], "coverage": {
            "lecture_concepts": 0, "grounded_concepts": 0, "uncovered_concepts": 0},
        "auto_approved": False, "database_writes": False,
    }
    return {**planned, "extraction": {
        "method": extracted["extraction_method"],
        "requires_review": True,
        "candidate_count": len(concepts),
        "no_candidates_found": not bool(concepts),
    }, "lecture_text_stored": False}


def prepare_staging_jobs(conn, owner_uid, lecture_text, *, textbook_id,
                         item_id_factory, mode="NCE", format="MC", count=1,
                         domain=None, section=None, objective=None):
    """Compose extraction, indexed retrieval, blueprint selection and v2 handoff.

    Produces preflight requests only. No network calls, paid AI generation,
    draft persistence, or publication. The trusted authenticated service must
    execute any generated jobs separately after explicit owner authorization.
    """
    if not isinstance(textbook_id, str) or not textbook_id.strip():
        raise ValueError("Explicit indexed textbook ID required")
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("Question count must be between 1 and 100")
    from lecture_generation_requests import requests, staging_http_jobs
    planned = prepare(conn, owner_uid, lecture_text, textbook_id=textbook_id,
                      count=count)
    selected = requests(planned, mode=mode, domain=domain,
                        section=section, objective=objective, format=format)
    handoff = staging_http_jobs(selected, textbook_id=textbook_id,
                                item_id_factory=item_id_factory, execute=False)
    return {"lecture_plan": planned, "classification": {
                "held_for_classification": selected["held_for_classification"],
                "held_count": selected["held_count"]},
            **handoff, "auto_generate": False, "auto_publish": False,
            "database_writes": False}
