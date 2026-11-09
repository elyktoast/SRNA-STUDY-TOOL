"""Validate a separately supplied clinical evidence adjudication result.

The caller must use an independently authenticated reviewer; this module
validates traceability and consistency, not medical truth. Never publishes.
"""


def evaluate(item, retrieval, judgments):
    if not isinstance(item, dict) or item.get("format") not in ("MC", "MS"):
        raise ValueError("MC/MS item required")
    options = item.get("options")
    keys = item.get("key")
    if not isinstance(options, list) or not options or not isinstance(keys, list) or not keys:
        raise ValueError("Complete item required")
    ids = [o.get("id") for o in options if isinstance(o, dict)]
    if len(ids) != len(options) or len(set(ids)) != len(ids) or any(k not in ids for k in keys):
        raise ValueError("Invalid item option IDs or key")
    if not isinstance(retrieval, dict) or not isinstance(retrieval.get("option_audits"), list):
        raise ValueError("Independent retrieval required")
    audits = {a.get("option_id"): a for a in retrieval["option_audits"] if isinstance(a, dict)}
    if set(audits) != set(ids) or len(audits) != len(ids):
        raise ValueError("Complete independent option retrieval required")
    if not isinstance(judgments, list):
        raise ValueError("Reviewer judgments required")
    reviews = {j.get("option_id"): j for j in judgments if isinstance(j, dict)}
    if len(reviews) != len(judgments) or set(reviews) != set(ids):
        raise ValueError("One independent judgment per option required")
    issues = []
    for option_id in ids:
        a, j = audits[option_id], reviews[option_id]
        expected = "supports_key" if option_id in keys else "refutes_distractor"
        available = a.get("retrieved_passage_ids")
        cited = j.get("passage_ids")
        verdict = j.get("verdict")
        explanation = j.get("explanation")
        contradiction = j.get("contradiction_found")
        if a.get("search_status") == "failed" or not isinstance(available, list) or not available:
            issues.append({"rule_id": "R-12.4", "option_id": option_id, "message": "Independent evidence unavailable"})
        if (not isinstance(cited, list) or not cited or not isinstance(available, list)
                or any(pid not in available for pid in cited)):
            issues.append({"rule_id": "R-12.4", "option_id": option_id, "message": "Reviewer citations not grounded in retrieved evidence"})
        if verdict != expected:
            issues.append({"rule_id": "R-12.4", "option_id": option_id, "message": "Option support/refutation not established"})
        if not isinstance(explanation, str) or not explanation.strip():
            issues.append({"rule_id": "R-12.4", "option_id": option_id, "message": "Reviewer explanation missing"})
        if contradiction is not False:
            issues.append({"rule_id": "R-12.4", "option_id": option_id, "message": "Contradiction absent not established"})
    return {"status": "pending" if issues else "reviewed",
            "issues": issues,
            "clinical_truth_verified": False,
            "human_review_required": True,
            "can_publish": False}
