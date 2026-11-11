"""Build grounded lecture concept requests with conservative blueprint selection.

This module never calls providers, writes drafts, or grants publication approval.
Unclassified and ambiguous topics are explicitly held for review.
"""
from item_generation_contract_v2 import build_step
from item_board_quality_v2 import classification
from nbcrna_classifier import suggest
from nbcrna_taxonomy import SECTIONS, OBJECTIVES

_DOMAIN_CODES = dict(zip(("I", "II", "III", "IV"), SECTIONS))


def _candidate_blueprint(title):
    result = suggest(title)
    if result["status"] != "suggested":
        return None, result["status"]
    candidate = result["candidates"][0]
    domain = next((code for code, group in _DOMAIN_CODES.items()
                   if group == candidate["domain"]), None)
    labels = OBJECTIVES.get(candidate["domain"], {}).get(candidate["section"], [])
    if domain is None or candidate["objective"] not in labels:
        return None, "unclassified"
    objective = f"{domain}.{candidate['section']}.{labels.index(candidate['objective']) + 1}"
    try:
        classification(domain, candidate["section"], objective)
    except ValueError:
        return None, "unclassified"
    return {"domain": domain, "section": candidate["section"],
            "objective": objective}, "candidate_requires_review"


def requests(plan, *, mode, domain=None, section=None, objective=None, format="MC"):
    if mode not in ("NCE", "SEE"):
        raise ValueError("Invalid exam mode")
    if not isinstance(plan, dict) or not isinstance(plan.get("topics"), list):
        raise ValueError("Grounded lecture plan required")
    explicit = (domain, section, objective)
    if any(value is not None for value in explicit):
        if not all(value is not None for value in explicit):
            raise ValueError("Provide all blueprint fields or none")
        classification(domain, section, objective)
    result, held = [], []
    for topic in plan["topics"]:
        count = topic.get("question_count")
        if type(count) is not int or count < 0:
            raise ValueError("Invalid topic allocation")
        if not count:
            continue
        if not isinstance(topic.get("title"), str) or not topic["title"].strip():
            raise ValueError("Lecture topic title required")
        if not isinstance(topic.get("evidence"), list) or not topic["evidence"]:
            raise ValueError("Grounded textbook evidence required")
        if all(value is not None for value in explicit):
            target = {"domain": domain, "section": section, "objective": objective}
            status = "user_selected_requires_review"
        else:
            target, status = _candidate_blueprint(topic["title"])
        if target is None:
            held.append({"topic": topic["title"], "lecture_locator": topic.get("lecture_locator"),
                         "question_count": count, "reason": status})
            continue
        for index in range(count):
            step = build_step("concept_card", mode=mode, **target,
                              evidence=topic["evidence"], topic=topic["title"])
            result.append({"topic": topic["title"],
                           "lecture_locator": topic.get("lecture_locator"),
                           "question_slot": index + 1,
                           "requested_format": format,
                           "classification": {**target, "status": status,
                                              "verified": False},
                           "concept_request": step,
                           "status": "awaiting_concept_generation"})
    return {"requests": result, "count": len(result),
            "held_for_classification": held,
            "held_count": sum(item["question_count"] for item in held),
            "auto_generate": False, "auto_publish": False,
            "database_writes": False}
