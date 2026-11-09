"""Report independent option retrieval as pending clinical verification.

Retrieval is not entailment, refutation, or contradiction adjudication.
"""
def attach(result, audit):
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
    stages["independent_option_evidence"] = {
        "status": "pending", "issues": [], "reason": reason}
    pending = list(screening.get("pending_verifications") or [])
    if "independent_option_evidence" not in pending:
        pending.append("independent_option_evidence")
    return {**result, "screening": {**screening, "stages": stages,
            "pending_verifications": pending, "screening_complete": False,
            "can_publish": False}, "can_publish": False,
            "requires_human_review": True}
