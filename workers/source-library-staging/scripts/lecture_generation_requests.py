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
    if format not in ("MC", "MS", "SA", "DD", "HS"):
        raise ValueError("Unsupported question format")
    if not isinstance(plan, dict) or not isinstance(plan.get("topics"), list):
        raise ValueError("Grounded lecture plan required")
    explicit = (domain, section, objective)
    if any(value is not None for value in explicit):
        if not all(value is not None for value in explicit):
            raise ValueError("Provide all blueprint fields or none")
        normalized = classification(domain, section, objective)
        domain, section, objective = (normalized["domain"], normalized["section"],
                                      normalized["objective"])
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
                              evidence=topic["evidence"], topic=topic["title"],
                              format=format)
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


def staging_http_jobs(prepared, *, textbook_id, item_id_factory, execute=False):
    """Adapt a classified lecture plan to the existing /generation/one contract.

    This is a request builder, not an HTTP client. The authenticated staging
    service must supply owner identity and enforce its own generation, review,
    checkpoint and unpublished-draft safeguards. Never silently enable paid calls.
    """
    if not isinstance(prepared, dict) or not isinstance(prepared.get("requests"), list):
        raise ValueError("Prepared lecture requests required")
    if not isinstance(textbook_id, str) or not textbook_id.strip():
        raise ValueError("Explicit indexed textbook ID required")
    if not callable(item_id_factory):
        raise ValueError("Trusted item ID factory required")
    if type(execute) is not bool:
        raise ValueError("Invalid execution flag")
    from uuid import UUID
    jobs = []
    seen = set()
    for entry in prepared["requests"]:
        if not isinstance(entry, dict) or entry.get("status") != "awaiting_concept_generation":
            raise ValueError("Only prepared concept requests may be submitted")
        classification_data = entry.get("classification")
        request = entry.get("concept_request")
        if not isinstance(classification_data, dict) or not isinstance(request, dict):
            raise ValueError("Validated classification and concept request required")
        if classification_data.get("status") != "candidate_requires_review" and classification_data.get("status") != "user_selected_requires_review":
            raise ValueError("Unsupported blueprint selection status")
        target = {key: classification_data.get(key) for key in ("domain", "section", "objective")}
        classification(**target)
        evidence = request.get("evidence")
        if (not isinstance(evidence, list) or not evidence
                or not any(isinstance(p, dict) and p.get("textbook_id") == textbook_id
                           for p in evidence)):
            raise ValueError("Selected textbook does not match grounded evidence")
        if request.get("step") != "concept_card" or request.get("topic") != entry.get("topic"):
            raise ValueError("Concept request topic mismatch")
        if any(request.get(key) != value for key, value in target.items()):
            raise ValueError("Concept request blueprint mismatch")
        if request.get("mode") not in ("NCE", "SEE"):
            raise ValueError("Invalid generation mode")
        fmt = entry.get("requested_format")
        if fmt not in ("MC", "MS", "SA", "DD", "HS"):
            raise ValueError("Unsupported format")
        item_id = item_id_factory()
        try:
            normalized_id = str(UUID(item_id))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Item ID factory must return UUID strings") from None
        if normalized_id in seen:
            raise ValueError("Duplicate item ID")
        seen.add(normalized_id)
        jobs.append({"path": "/generation/one" if execute else "/generation/preflight",
                     "body": {"topic": entry["topic"], "mode": request["mode"],
                              **target, "format": fmt, "item_id": normalized_id,
                              "textbook_id": textbook_id}})
    return {"jobs": jobs, "count": len(jobs), "paid_calls_requested": execute,
            "auto_publish": False, "database_writes": False}
