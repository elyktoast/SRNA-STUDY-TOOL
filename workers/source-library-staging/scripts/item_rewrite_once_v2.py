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
               "max_rewrites": 1, "requires_human_review": True,
               "repair_instructions": (
                   "Fix only the reported rule-ID issues. Preserve the question's "
                   "clinical meaning, answer key, protected metadata, concept "
                   "evidence IDs, and all unaffected fields. For R-2.5, use only "
                   "exact verbatim excerpts and matching source IDs/pages from "
                   "trusted evidence; never invent a citation. For R-12.4, give "
                   "every option an evidence-grounded verdict, valid passage IDs, "
                   "and an explanation; source silence cannot refute a distractor. "
                   "If the supplied evidence is insufficient, do not fabricate "
                   "a repair. Return the complete revised item as a JSON object. "
                   "The result remains unpublished and requires clinical review."
               )}
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
            {"rule_id": "R-13", "message": "Rewrite attempted to change protected metadata"}] + deepcopy(issues),
            "rewrite_attempts": 1, "can_publish": False}
    prior = original.get("concept_card")
    revised = candidate.get("concept_card")
    if isinstance(prior, dict) and (
            not isinstance(revised, dict) or
            prior.get("evidence_ids") != revised.get("evidence_ids")):
        return {"item": deepcopy(original), "issues": deepcopy(issues) + [
            {"rule_id": "R-2.5", "message": "Rewrite changed concept evidence references"}],
            "rewrite_attempts": 1, "can_publish": False}
    if candidate.get("status") != "draft":
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-13", "message": "Rewrite cannot change draft review state"}] + deepcopy(issues),
            "rewrite_attempts": 1, "can_publish": False}
    try:
        checked = validate(deepcopy(candidate))
    except Exception:
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    if not isinstance(checked, list):
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    return {"item": deepcopy(candidate), "issues": checked,
            "rewrite_attempts": 1, "can_publish": False}
