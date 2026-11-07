"""Isolated v2.0 three-call generator orchestrator.

The caller supplies a trusted, authenticated model adapter callable. No default
network transport or paid model invocation is provided. Responses remain drafts.
"""
from item_generation_contract_v2 import build_step, validate_complete_item
from item_source_reconciliation_v2 import reconcile
from item_answer_evidence_v2 import check as answer_evidence_check
from item_special_format_evidence_v2 import check as special_evidence_check

CONCEPT_FIELDS = ("objective", "mechanism", "relevance", "misconception",
                  "counterfactual", "evidence_ids")
RATIONALE_FIELDS = ("core_concept", "why_key_wins", "trap", "distractor_breakdown")


def _response(adapter, request):
    try:
        result = adapter(request)
    except Exception as exc:
        # Expose only a fixed step identifier to the authenticated HTTP bridge.
        # Never attach prompts, evidence, model output or credentials.
        if request.get("step") in ("concept_card", "item_draft", "rationale"):
            exc.generation_step = request["step"]
        raise
    if not isinstance(result, dict):
        raise ValueError("Model adapter must return a JSON object")
    return result



def _complete_nonclinical_schema_fields(draft):
    """Fill only absent/empty administrative placeholders; never synthesize clinical evidence.

    Empty audit/self_check/stats mean NOT EVALUATED, not passed. Source quotes,
    keyed answer evidence and clinical judgments remain mandatory validations.
    """
    item = dict(draft)
    for field in ("sa", "dd", "hs"):
        if field not in item and item.get("format") not in (field.upper(),):
            item[field] = None
    for field, empty in (("audit", []), ("self_check", {}), ("stats", {})):
        if item.get(field) is None:
            item[field] = empty.copy()
    return item


def generate_one(adapter, *, mode, domain, section, objective, evidence,
                 format="MC", item_id, checkpoint=None, on_checkpoint=None,
                 generator_model_id=None):
    if not callable(adapter):
        raise ValueError("Explicit authenticated model adapter required")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("New item ID required")
    if format not in ("MC", "MS", "SA", "DD", "HS"):
        raise ValueError("Unsupported v2.0 question format")
    if not isinstance(evidence, list) or not evidence or any(
        not isinstance(p, dict) or not all(p.get(k) for k in ("passage_id", "textbook_id", "excerpt"))
        for p in evidence
    ):
        raise ValueError("Verified indexed evidence references required")
    passage_ids = [p["passage_id"] for p in evidence]
    if len(set(passage_ids)) != len(passage_ids):
        raise ValueError("Duplicate passage IDs in evidence bundle")
    args = dict(mode=mode, domain=domain, section=section,
                objective=objective, evidence=evidence)
    if checkpoint is not None and (not isinstance(checkpoint, dict) or set(checkpoint) - {"concept_card", "draft"} or ("draft" in checkpoint and "concept_card" not in checkpoint)):
        raise ValueError("Invalid resume checkpoint")
    if on_checkpoint is not None and not callable(on_checkpoint):
        raise ValueError("Checkpoint writer must be callable")
    checkpoint = checkpoint or {}
    concept = checkpoint.get("concept_card") if "concept_card" in checkpoint else _response(adapter, build_step("concept_card", **args))
    # Some JSON-mode providers wrap the requested object under its step name.
    # Unwrap only the exact one-key envelope; never invent missing fields or IDs.
    if isinstance(concept, dict) and set(concept) == {"concept_card"} and isinstance(concept["concept_card"], dict):
        concept = concept["concept_card"]
    if not isinstance(concept, dict):
        raise ValueError("Concept card incomplete; draft generation blocked")
    if any(not isinstance(concept.get(field), str) or not concept[field].strip()
           for field in CONCEPT_FIELDS if field != "evidence_ids") or not concept.get("evidence_ids"):
        raise ValueError("Concept card incomplete; draft generation blocked")
    if not isinstance(concept["evidence_ids"], list) or len(concept["evidence_ids"]) != len(set(map(str, concept["evidence_ids"]))):
        raise ValueError("Concept card must reference unique passage IDs")
    if concept["objective"].strip() != objective.strip():
        raise ValueError("Concept card objective differs from selected blueprint objective")
    allowed_ids = {p["passage_id"] for p in evidence}
    ids = concept["evidence_ids"]
    if not isinstance(ids, list) or not ids or not all(
        isinstance(pid, str) and pid in allowed_ids for pid in ids
    ):
        raise ValueError("Concept card references unknown passages")
    if "concept_card" not in checkpoint and on_checkpoint is not None:
        on_checkpoint("concept_card", concept)
    draft = checkpoint.get("draft") if "draft" in checkpoint else _response(adapter, build_step("item_draft", **args,
                                        format=format, concept_card=concept))
    if not isinstance(draft, dict):
        raise ValueError("Generated draft has wrong format or missing stem")
    if set(draft) == {"draft"} and isinstance(draft["draft"], dict):
        draft = draft["draft"]
    if draft.get("format") != format or not isinstance(draft.get("stem"), str):
        raise ValueError("Generated draft has wrong format or missing stem")
    if "draft" not in checkpoint and on_checkpoint is not None:
        on_checkpoint("draft", draft)
    rationale = _response(adapter, build_step("rationale", **args, format=format,
                                             concept_card=concept, draft=draft))
    if any(not rationale.get(field) for field in RATIONALE_FIELDS):
        raise ValueError("Rationale incomplete")
    # The model must not be allowed to overwrite identifiers, source, or approval.
    item = {**_complete_nonclinical_schema_fields(draft), "item_id": item_id, "rules_version": "2.0",
            "mode": mode, "domain": domain, "section": section,
            "objective": objective, "format": format,
            "concept_card": concept, "rationale": rationale,
            "status": "draft"}
    if generator_model_id is not None:
        if not isinstance(generator_model_id, str) or not generator_model_id.strip():
            raise ValueError("Trusted generator model identity must be nonempty")
        item["model"] = generator_model_id
    issues = validate_complete_item(item)
    citation_issues = reconcile(item, evidence)
    issues.extend(citation_issues)
    issues.extend(answer_evidence_check(item, evidence) if format in ("MC", "MS")
                  else special_evidence_check(item, evidence))
    return {"item": item, "schema_issues": issues,
            "requires_human_review": True, "auto_approved": False,
            "database_writes": False, "ready_for_intake": not bool(issues)}
