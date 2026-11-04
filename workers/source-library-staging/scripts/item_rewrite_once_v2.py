"""One-rewrite limit for unpublished v2 draft repair.

The caller supplies a trusted rewrite callable. No network or database writes.
A failed rewrite remains flagged for human review; never auto-approves.
"""
from copy import deepcopy


def attempt_once(original, issues, rewrite, validate):
    if not isinstance(original, dict) or not isinstance(issues, list):
        raise ValueError("Original draft and diagnostic list required")
    if not callable(rewrite) or not callable(validate):
        raise ValueError("Explicit rewrite and validation callables required")
    if not issues:
        return {"item": deepcopy(original), "issues": [],
                "rewrite_attempts": 0, "can_publish": False}
    immutable = ("item_id", "rules_version", "mode", "domain", "section",
                 "objective", "format", "model", "status")
    request = {"item": deepcopy(original), "issues": deepcopy(issues),
               "max_rewrites": 1, "requires_human_review": True}
    try:
        candidate = rewrite(request)
    except Exception:
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    if not isinstance(candidate, dict):
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    if any(candidate.get(field) != original.get(field) for field in immutable):
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-13", "message": "Rewrite attempted to change protected metadata"}],
            "rewrite_attempts": 1, "can_publish": False}
    if candidate.get("status") != "draft":
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-13", "message": "Rewrite cannot change draft review state"}],
            "rewrite_attempts": 1, "can_publish": False}
    checked = validate(deepcopy(candidate))
    if not isinstance(checked, list):
        raise ValueError("Validator must return diagnostic list")
    return {"item": deepcopy(candidate), "issues": checked,
            "rewrite_attempts": 1, "can_publish": False}
