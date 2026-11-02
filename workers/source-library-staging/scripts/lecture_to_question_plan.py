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
