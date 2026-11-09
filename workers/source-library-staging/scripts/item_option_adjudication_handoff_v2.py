"""Optional independent option adjudication handoff; no provider transport.

A validated reviewer report remains subject to clinical human review.
"""
from item_option_adjudication_v2 import evaluate


def run(item, retrieval, reviewer, *, source_passages, generator_model_id, reviewer_model_id):
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
    if not isinstance(source_passages, list):
        raise ValueError("Trusted independently retrieved source passages required")
    indexed = {p.get("passage_id"): p for p in source_passages
               if isinstance(p, dict) and isinstance(p.get("passage_id"), str)
               and isinstance(p.get("excerpt"), str) and p["excerpt"].strip()}
    referenced = {pid for a in retrieval.get("option_audits", [])
                  for pid in a.get("retrieved_passage_ids", [])}
    if not referenced or not referenced.issubset(indexed):
        return {"status": "pending", "issues": [{"rule_id": "R-12.4",
                "message": "Independent source passage text unavailable"}],
                "clinical_truth_verified": False, "can_publish": False}
    # Pass a restricted request: the reviewer must return source-grounded
    # judgments, and the caller must provide authenticated source access.
    request = {"stem": item.get("stem"), "options": item.get("options"),
               "retrieval": retrieval, "source_passages": [indexed[pid] for pid in sorted(referenced)], "task": "independent_option_adjudication"}
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
