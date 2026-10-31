"""Isolated v2.0 three-call generator orchestrator.

The caller supplies a trusted, authenticated model adapter callable. No default
network transport or paid model invocation is provided. Responses remain drafts.
"""
from item_generation_contract_v2 import build_step, validate_complete_item
from item_source_reconciliation_v2 import reconcile

CONCEPT_FIELDS = ("objective", "mechanism", "relevance", "misconception",
                  "counterfactual", "evidence_ids")
RATIONALE_FIELDS = ("core_concept", "why_key_wins", "trap", "distractor_breakdown")


def _response(adapter, request):
    result = adapter(request)
    if not isinstance(result, dict):
        raise ValueError("Model adapter must return a JSON object")
    return result


def generate_one(adapter, *, mode, domain, section, objective, evidence,
                 format="MC", item_id):
    if not callable(adapter):
        raise ValueError("Explicit authenticated model adapter required")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("New item ID required")
    args = dict(mode=mode, domain=domain, section=section,
                objective=objective, evidence=evidence)
    concept = _response(adapter, build_step("concept_card", **args))
    if any(not concept.get(field) for field in CONCEPT_FIELDS):
        raise ValueError("Concept card incomplete; draft generation blocked")
    allowed_ids = {p["passage_id"] for p in evidence}
    ids = concept["evidence_ids"]
    if not isinstance(ids, list) or not ids or not all(
        isinstance(pid, str) and pid in allowed_ids for pid in ids
    ):
        raise ValueError("Concept card references unknown passages")
    draft = _response(adapter, build_step("item_draft", **args,
                                        format=format, concept_card=concept))
    if draft.get("format") != format or not isinstance(draft.get("stem"), str):
        raise ValueError("Generated draft has wrong format or missing stem")
    rationale = _response(adapter, build_step("rationale", **args, format=format,
                                             concept_card=concept, draft=draft))
    if any(not rationale.get(field) for field in RATIONALE_FIELDS):
        raise ValueError("Rationale incomplete")
    # The model must not be allowed to overwrite identifiers, source, or approval.
    item = {**draft, "item_id": item_id, "rules_version": "2.0",
            "mode": mode, "domain": domain, "section": section,
            "objective": objective, "format": format,
            "concept_card": concept, "rationale": rationale,
            "status": "draft"}
    issues = validate_complete_item(item)
    citation_issues = reconcile(item, evidence)
    issues.extend(citation_issues)
    return {"item": item, "schema_issues": issues,
            "requires_human_review": True, "auto_approved": False,
            "database_writes": False, "ready_for_intake": not bool(issues)}
