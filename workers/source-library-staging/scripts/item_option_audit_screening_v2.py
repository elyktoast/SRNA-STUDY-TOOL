"""Report independent option retrieval as pending clinical verification.

Retrieval is not entailment, refutation, or contradiction adjudication.
"""
def attach(result, audit, adjudication=None):
    if not isinstance(result, dict):
        raise ValueError("Screening result required")
    screening = result.get("screening")
    if not isinstance(screening, dict) or not isinstance(screening.get("stages"), dict):
        return result
    if not isinstance(audit, dict):
        reason = "Independent option search not available"
    elif audit.get("all_options_searched") is False:
        reason = "One or more independent option searches failed"
    elif audit.get("all_options_have_matches") is False:
        reason = "One or more options had no matching indexed passages"
    else:
        reason = "Retrieved option passages still require clinical support/refutation and contradiction verification"
    stages = dict(screening["stages"])
    reviewed = (isinstance(adjudication, dict) and adjudication.get("status") == "reviewed"
                and adjudication.get("issues") == []
                and adjudication.get("clinical_truth_verified") is False
                and adjudication.get("human_review_required") is True
                and isinstance(adjudication.get("generator_model_id"), str)
                and isinstance(adjudication.get("reviewer_model_id"), str)
                and adjudication["generator_model_id"].strip()
                and adjudication["reviewer_model_id"].strip()
                and adjudication["generator_model_id"] != adjudication["reviewer_model_id"])
    stages["independent_option_evidence"] = {
        "status": "pass" if reviewed else "pending",
        "issues": adjudication.get("issues", []) if isinstance(adjudication, dict) else [],
        "reason": "Independent source-grounded model adjudication completed; human clinical review remains required" if reviewed else reason}
    if isinstance(adjudication, dict):
        screening = {**screening, "independent_option_adjudication": adjudication}
    pending = list(screening.get("pending_verifications") or [])
    if reviewed:
        pending = [p for p in pending if p != "independent_option_evidence"]
    if not reviewed and "independent_option_evidence" not in pending:
        pending.append("independent_option_evidence")
    return {**result, "screening": {**screening, "stages": stages,
            "pending_verifications": pending, "screening_complete": False,
            "can_publish": False}, "can_publish": False,
            "requires_human_review": True}
