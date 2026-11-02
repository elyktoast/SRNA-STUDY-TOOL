"""Build v2.0 generation requests from a grounded lecture coverage plan.

This is a read-only handoff: no provider calls, draft storage, or publication.
The caller must review extracted concepts and select an NBCRNA classification.
"""
from item_generation_contract_v2 import build_step

def requests(plan, *, mode, domain, section, objective, format="MC"):
    if not isinstance(plan, dict) or not isinstance(plan.get("topics"), list):
        raise ValueError("Grounded lecture plan required")
    result = []
    for topic in plan["topics"]:
        count = topic.get("question_count")
        if type(count) is not int or count < 0:
            raise ValueError("Invalid topic allocation")
        for index in range(count):
            step = build_step("concept_card", mode=mode, domain=domain,
                              section=section, objective=objective,
                              evidence=topic["evidence"])
            result.append({"topic": topic["title"],
                           "lecture_locator": topic.get("lecture_locator"),
                           "question_slot": index + 1,
                           "requested_format": format,
                           "concept_request": step,
                           "status": "awaiting_concept_generation"})
    return {"requests": result, "count": len(result), "auto_generate": False,
            "auto_publish": False, "database_writes": False}
