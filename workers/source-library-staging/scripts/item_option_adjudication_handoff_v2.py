"""Optional independent option adjudication handoff; no provider transport.

A validated reviewer report remains subject to clinical human review.
"""
from item_option_adjudication_v2 import evaluate


def run(item, retrieval, reviewer, *, generator_model_id, reviewer_model_id):
    if not callable(reviewer):
        raise ValueError("Independent option reviewer adapter required")
    if (not isinstance(generator_model_id, str) or not generator_model_id.strip()
            or not isinstance(reviewer_model_id, str) or not reviewer_model_id.strip()
            or generator_model_id.strip() == reviewer_model_id.strip()):
        raise ValueError("Distinct generator and reviewer model identities required")
    if not isinstance(retrieval, dict) or retrieval.get("all_options_searched") is not True:
        return {"status": "pending", "issues": [{"rule_id": "R-12.4",
                "message": "Independent option retrieval incomplete"}],
                "clinical_truth_verified": False, "can_publish": False}
    # Pass a restricted request: the reviewer must return source-grounded
    # judgments, and the caller must provide authenticated source access.
    request = {"stem": item.get("stem"), "options": item.get("options"),
               "retrieval": retrieval, "task": "independent_option_adjudication"}
    try:
        response = reviewer(request)
        report = evaluate(item, retrieval, response)
    except Exception:
        return {"status": "pending", "issues": [{"rule_id": "R-12.4",
                "message": "Independent option adjudication unavailable or invalid"}],
                "clinical_truth_verified": False, "can_publish": False}
    return {**report, "generator_model_id": generator_model_id,
            "reviewer_model_id": reviewer_model_id,
            "can_publish": False}
