"""Phase A end-to-end offline screening for NEW v2.0 draft questions.

No paid model calls, no database writes, no approvals. Model and reviewer
responses are independently supplied and cannot be self-attested by item JSON.
"""
from item_validation_pipeline import screen as structural_screen
from item_semantic_duplicates import screen as semantic_screen
from item_blind_review_scoring import compare as compare_blind


def screen(item, *, known_stems=(), source_texts=(), passages=None,
           calculation=None, embedding=None, neighbors=None, blind_response=None):
    result = structural_screen(item, known_stems=known_stems,
                               source_texts=source_texts, passages=passages,
                               calculation=calculation)
    stages = result["stages"]
    if stages["schema"]["status"] != "pass":
        return result
    # Exact-stem screening alone does not establish semantic uniqueness.
    if embedding is None or neighbors is None:
        if stages["duplicates"]["status"] == "pass":
            stages["duplicates"] = {"status": "pending", "issues": []}
    if embedding is not None and neighbors is not None:
        try:
            matches = semantic_screen(embedding, neighbors)
        except (ValueError, KeyError, TypeError) as exc:
            stages["duplicates"] = {"status": "fail", "issues": [
                {"rule_id": "R-12.9", "message": "Embedding screening invalid: " + str(exc)}]}
        else:
            if matches:
                stages["duplicates"] = {"status": "flag", "issues": [
                    {"rule_id": "R-12.9", "message": "Potential semantic duplicate", "matches": matches}]}
            elif stages["duplicates"]["status"] == "pass":
                stages["duplicates"] = {"status": "pass", "issues": []}
    # A blind response is only trustworthy when produced by an independently
    # authenticated blind reviewer. This function never grants approval.
    if blind_response is not None:
        issues = compare_blind(item, blind_response)
        stages["blind_model"] = {"status": "fail" if issues else "pass", "issues": issues}
    # No caller-supplied data can mark the human review stage passed.
    stages["human_review"] = {"status": "pending", "issues": []}
    if stages["evidence"]["status"] == "fail":
        result["next_state"] = "needs_source_review"
    elif any(stages[name]["status"] in ("fail", "flag")
             for name in ("deterministic_text", "math", "duplicates", "blind_model")):
        result["next_state"] = "needs_clinical_review" if stages["blind_model"]["status"] == "fail" else "needs_editorial_review"
    result["screening_complete"] = all(
        stages[name]["status"] == "pass"
        for name in ("schema", "deterministic_text", "math", "evidence",
                     "duplicates", "blind_model")
    )
    result["can_publish"] = False
    return result
