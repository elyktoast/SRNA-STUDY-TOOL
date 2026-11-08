"""Validation contract for private staging question drafts; no network or database writes."""
from uuid import UUID

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
    if any(not isinstance(x, dict) or not x.get("passage_id")
           or str(x.get("textbook_id")) != str(payload["textbook_id"])
           for x in evidence):
        raise ValueError("Evidence must match textbook")
    return {"status": "pending_review", "requires_human_review": True,
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
