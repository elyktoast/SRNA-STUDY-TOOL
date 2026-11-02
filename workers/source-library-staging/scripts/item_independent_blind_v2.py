"""Run an explicitly supplied independent blind-review adapter.

No network/default model, no key/rationale/source disclosure, no approval.
Caller must authenticate and verify model separation outside this module.
"""
from item_blind_review import payload
from item_blind_review_scoring import compare

def review(item, reviewer, *, generator_model_id, reviewer_model_id):
    if not callable(reviewer):
        raise ValueError("Independent reviewer adapter required")
    if not isinstance(generator_model_id, str) or not generator_model_id.strip():
        raise ValueError("Generator model identity required")
    if not isinstance(reviewer_model_id, str) or not reviewer_model_id.strip():
        raise ValueError("Reviewer model identity required")
    if generator_model_id.strip() == reviewer_model_id.strip():
        raise ValueError("Blind reviewer must use a different model identity")
    request = payload(item)
    if not isinstance(request.get("stem"), str) or not request["stem"].strip():
        raise ValueError("Blind item stem required")
    response = reviewer(request)
    issues = compare(item, response)
    return {"status": "flag" if issues else "pass", "issues": issues,
            "generator_model_id": generator_model_id,
            "reviewer_model_id": reviewer_model_id,
            "human_review_required": True, "can_publish": False,
            "model_separation_attested_by_caller": True}
