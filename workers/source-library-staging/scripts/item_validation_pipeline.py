"""Phase A Section 12.1: fail-closed staged screening for NEW v2.0 items.

Only schema/text stages run here. Math recomputation, passage resolution,
embedding similarity, blind model screening and human approval require
separate verified integrations; never mark them passed by default.
"""
import re
from item_standard_v2 import check
from item_duplicate_checks import detect

STAGES = ("schema", "deterministic_text", "math", "evidence",
          "duplicates", "blind_model", "human_review")
PENDING = "pending"


def screen(item, *, known_stems=()):
    schema_errors = check(item)
    stages = {name: {"status": PENDING, "issues": []} for name in STAGES}
    stages["schema"] = {"status": "fail" if schema_errors else "pass",
                        "issues": schema_errors}
    if schema_errors:
        return {"can_publish": False, "stages": stages,
                "next_state": "needs_source_review" if any(
                    e["rule_id"] == "R-2.5" for e in schema_errors) else "draft",
                "rewrite_attempts_allowed": 1}
    issues = []
    if item["format"] in ("MC", "MS"):
        for option in item["options"]:
            if re.search(r"\b(always|never|only|sole|all|none|completely)\b", option["text"], re.I):
                issues.append({"rule_id": "R-6.10", "message": "Absolute wording requires editorial review"})
        if any(re.search(r"\b(all|none) of the above\b", option["text"], re.I) for option in item["options"]):
            issues.append({"rule_id": "R-6.11", "message": "Forbidden option"})
    stages["deterministic_text"] = {"status": "flag" if issues else "pass", "issues": issues}
    duplicates = detect(item, known_stems)
    stages["duplicates"] = {"status": "fail" if duplicates else "pass", "issues": duplicates}
    return {"can_publish": False, "stages": stages,
            "next_state": "needs_editorial_review" if issues or duplicates else "draft",
            "rewrite_attempts_allowed": 1}
