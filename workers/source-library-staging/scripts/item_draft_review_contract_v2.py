"""Validation contract for private staging question drafts; no network or database writes."""
from uuid import UUID
from item_source_scope_v2 import source_scope

def approval_issues(screening, format):
    """Saved independent failures cannot be cleared by citation-only validation."""
    required = {"schema", "deterministic_text", "math", "evidence", "duplicates",
                "blind_model", "explanation_evidence"}
    if format in ("MC", "MS"):
        required.update(("editorial_quality", "options_only", "independent_option_evidence"))
    elif format == "SA":
        required.add("page_image_verification")
    elif format == "HS":
        required.add("figure_verification")
    elif format != "DD":
        return [{"rule_id":"R-7.6", "message":"Unsupported question format cannot be approved"}]
    stages = screening.get("stages") if isinstance(screening, dict) else None
    stages = stages if isinstance(stages, dict) else {}
    names = required | (set(stages) - {"human_review"})
    issues = []
    for name in sorted(names):
        stage = stages.get(name)
        if (not isinstance(stage, dict) or stage.get("status") != "pass"
                or stage.get("issues", []) != []):
            issues.append({"rule_id":"R-12.10", "field":"screening.stages." + name,
                           "message":"Automated verification must pass before approval: " + name})
    return issues

def validate_draft(payload):
    if not isinstance(payload, dict):
        raise ValueError("Draft must be an object")
    for key in ("owner_uid", "textbook_id"):
        try:
            UUID(str(payload[key]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid " + key) from exc
    if payload.get("mode") not in ("NCE", "SEE"):
        raise ValueError("Invalid examination mode")
    if payload.get("format") not in ("MC", "MS", "SA", "DD", "HS"):
        raise ValueError("Invalid question format")
    if not isinstance(payload.get("question"), dict):
        raise ValueError("Question object required")
    if not isinstance(payload.get("screening"), dict):
        raise ValueError("Screening object required")
    evidence = payload.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Indexed evidence required")
    books = source_scope(payload['textbook_id'], payload.get('textbook_ids')) or [str(payload['textbook_id'])]
    if any(not isinstance(x, dict) or not x.get("passage_id")
           or str(x.get("textbook_id")) not in books
           for x in evidence):
        raise ValueError("Evidence must match textbook")
    if str(payload['textbook_id']) not in {str(x['textbook_id']) for x in evidence}:
        raise ValueError('Primary textbook must supply indexed evidence')
    stages = payload["screening"].get("stages", {})
    needs_revision = isinstance(stages, dict) and any(
        isinstance(stage, dict) and stage.get("status") in ("flag", "fail")
        for stage in stages.values())
    return {"status": "needs_revision" if needs_revision else "pending_review", "requires_human_review": True,
            "published": False}

def validate_review(status, reviewer_uid, notes):
    if status not in ("needs_revision", "approved_for_bank", "rejected"):
        raise ValueError("Invalid review decision")
    try:
        UUID(str(reviewer_uid))
    except (TypeError, ValueError) as exc:
        raise ValueError("Reviewer identity required") from exc
    if not isinstance(notes, str) or len(notes) > 5000:
        raise ValueError("Invalid notes")
    if status == "approved_for_bank" and not notes.strip():
        raise ValueError("Approval requires review notes")
    return {"status": status, "published": False}
