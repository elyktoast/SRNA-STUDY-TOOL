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
                    "If an option is ambiguous, potentially also correct, or its explanation lacks affirmative source support, repair the STEM conditions or replace the INCORRECT option with a distinct clinically plausible, demonstrably false alternative; never change the protected correct answer or its text. Supply a separate evidence-grounded explanation for EVERY option, including the correct one, and update distractor_evidence and rationale consistently. Do not infer that an answer is false just because a passage does not mention it. If the supplied evidence is insufficient, do not fabricate "
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
    # A rule-specific rewrite must not silently alter the answer.
    if candidate.get("key") != original.get("key"):
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-5.1", "message": "Rewrite changed answer key"}] + deepcopy(issues),
            "rewrite_attempts": 1, "can_publish": False}
    if original.get("format") in ("MC", "MS"):
        def keyed_texts(item):
            options = item.get("options")
            if not isinstance(options, list):
                return None
            lookup = {o.get("id"): o.get("text") for o in options if isinstance(o, dict)}
            return [lookup.get(k) for k in original.get("key", [])]
        if keyed_texts(candidate) != keyed_texts(original):
            return {"item": deepcopy(original), "issues": [
                {"rule_id": "R-5.1", "message": "Rewrite changed keyed option text"}] + deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False}
    for fmt, field, answer_field in (
            ("SA", "sa", "answer"), ("DD", "dd", "pairs"),
            ("HS", "hs", "correct_region")):
        if original.get("format") == fmt:
            before, after = original.get(field), candidate.get(field)
            if not isinstance(before, dict) or not isinstance(after, dict) or before.get(answer_field) != after.get(answer_field):
                return {"item": deepcopy(original), "issues": [
                    {"rule_id": "R-5.1", "message": "Rewrite changed protected answer"}] + deepcopy(issues),
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
