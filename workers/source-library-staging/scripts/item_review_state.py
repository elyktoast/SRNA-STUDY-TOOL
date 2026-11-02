"""Explicit reviewer-controlled state transitions for NEW v2.0 items.

No model, validator or generator can self-approve or self-publish.
Callers must authenticate and authorize reviewers outside this pure module.
"""
from datetime import datetime, timezone

STATES = {
    "draft": {"needs_source_review", "needs_clinical_review", "needs_editorial_review"},
    "needs_source_review": {"verified_evidence", "needs_editorial_review", "needs_clinical_review"},
    "needs_clinical_review": {"needs_editorial_review", "needs_source_review", "verified_evidence"},
    "needs_editorial_review": {"needs_source_review", "needs_clinical_review", "verified_evidence"},
    "verified_evidence": {"approved", "needs_source_review", "needs_clinical_review", "needs_editorial_review"},
    "approved": {"published", "needs_clinical_review", "retired"},
    "published": {"retired"},
    "retired": set(),
}
PRIVILEGED = {"verified_evidence", "approved", "published", "retired"}
ROLES = {"verified_evidence": "source_reviewer", "approved": "clinical_reviewer",
         "published": "publisher", "retired": "publisher"}


def transition(item, target, *, actor_id, actor_roles=(), checks=None, note=""):
    """Return a copied item with append-only audit; never modify input."""
    current = item.get("status")
    if target not in STATES.get(current, set()):
        raise ValueError("Invalid review-state transition")
    if not isinstance(actor_id, str) or not actor_id.strip():
        raise PermissionError("Authenticated reviewer ID required")
    if target in PRIVILEGED:
        if ROLES[target] not in actor_roles:
            raise PermissionError("Required reviewer role missing")
        if not isinstance(checks, dict):
            raise ValueError("Independent validation report required")
        stages = checks.get("stages")
        if not isinstance(stages, dict):
            raise ValueError("Validation stages missing")
        required = ("schema", "deterministic_text", "math", "evidence", "duplicates")
        if any(stages.get(stage, {}).get("status") != "pass" for stage in required):
            raise ValueError("Required deterministic checks not passed")
        if target in ("approved", "published") and any(
            stages.get(stage, {}).get("status") != "pass"
            for stage in ("blind_model", "human_review")
        ):
            raise ValueError("Independent blind and human reviews required")
    updated = dict(item)
    updated["status"] = target
    updated["audit"] = list(item.get("audit") or []) + [{
        "who": actor_id, "what_changed": current + " -> " + target,
        "date": datetime.now(timezone.utc).date().isoformat(), "note": note,
    }]
    return updated
