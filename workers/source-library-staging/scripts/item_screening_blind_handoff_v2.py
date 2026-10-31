"""Attach separately executed blind-review results to read-only screening.

Only a trusted server should call this after authenticating the reviewer and
verifying provider/model identity. Never approves or publishes a question.
"""
from copy import deepcopy

def attach(screening, blind_result):
    if not isinstance(screening, dict) or not isinstance(screening.get("stages"), dict):
        raise ValueError("Screening report required")
    if not isinstance(blind_result, dict) or blind_result.get("status") not in ("pass", "flag"):
        raise ValueError("Completed independent blind result required")
    if blind_result.get("human_review_required") is not True or blind_result.get("can_publish") is not False:
        raise ValueError("Unsafe blind-review result")
    if not blind_result.get("generator_model_id") or not blind_result.get("reviewer_model_id"):
        raise ValueError("Both model identities required")
    if blind_result["generator_model_id"] == blind_result["reviewer_model_id"]:
        raise ValueError("Generator and reviewer must differ")
    issues = blind_result.get("issues")
    if not isinstance(issues, list) or (blind_result["status"] == "pass" and issues) or (blind_result["status"] == "flag" and not issues):
        raise ValueError("Blind status and findings disagree")
    result = deepcopy(screening)
    stages = result["stages"]
    if "blind_model" not in stages or "human_review" not in stages:
        raise ValueError("Incomplete screening stages")
    stages["blind_model"] = {"status": blind_result["status"], "issues": issues}
    stages["human_review"] = {"status": "pending", "issues": []}
    result["screening_complete"] = all(
        stages.get(name, {}).get("status") == "pass"
        for name in ("schema", "deterministic_text", "math", "evidence",
                     "duplicates", "blind_model")
    )
    if blind_result["status"] == "flag":
        result["next_state"] = "needs_clinical_review"
    result["can_publish"] = False
    return result
