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


def _final_counterfactual(draft, proposal):
    """Bind an author's teaching edit to the finished stem, never approve it."""
    if not isinstance(proposal, dict) or set(proposal) != {"from_text", "to_text", "expected_key"}:
        raise ValueError("Rationale incomplete: invalid counterfactual")
    before, after, key = (proposal[k] for k in ("from_text", "to_text", "expected_key"))
    ids = {o.get("id") for o in draft.get("options", []) if isinstance(o, dict)}
    original = draft.get("key", [])
    if (not isinstance(original, list) or not original
            or any(not isinstance(k, str) or k not in ids for k in original)
            or any(not isinstance(s, str) or not s.strip() or len(s) > 200 for s in (before, after))
            or before == after or draft["stem"].count(before) != 1
            or before == draft["stem"] or not isinstance(key, list)
            or len(key) != len(original) or any(not isinstance(k, str) or k not in ids for k in key)
            or len(set(key)) != len(key) or set(key) == set(original)):
        raise ValueError("Rationale incomplete: invalid counterfactual")
    return f'If "{before}" is replaced by "{after}", the best response changes to option(s) {", ".join(key)}.'


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
    # This stage sees indexed text, never authenticated page-image verification.
    # A model assertion (or omitted flag) cannot create a verification receipt.
    item["numbers_verified_against_page_image"] = False
    for field in ("sa", "dd", "hs"):
        if field not in item and item.get("format") not in (field.upper(),):
            item[field] = None
    for field, empty in (("audit", []), ("self_check", {}), ("stats", {})):
        if item.get(field) is None:
            item[field] = empty.copy()
    return item


def _hydrate_indexed_citations(draft, trusted_passages):
    """Materialize missing quotations only from exactly bound indexed references.

    Never replace a supplied quote, repair a wrong source/page, or treat a
    reference as proof of clinical support. All existing validators still run.
    """
    import copy
    item = copy.deepcopy(draft)
    sources = {p["passage_id"]: p for p in trusted_passages}
    citations = item.get("evidence")
    if not isinstance(citations, list):
        return item
    for citation in citations:
        if isinstance(citation, dict):
            citation.pop("numbers_verified_against_page_image", None)
        if not isinstance(citation, dict) or "excerpt" in citation:
            continue
        source = sources.get(citation.get("passage_id"))
        if (source is not None
                and citation.get("textbook_id") == source.get("textbook_id")
                and type(citation.get("pdf_page")) is int
                and citation["pdf_page"] == source.get("pdf_page_start")):
            citation["excerpt"] = source["excerpt"]
    # Option evidence already names its source IDs. Materialize any omitted
    # citations from those trusted references; unknown IDs remain unresolved.
    cited = {c.get("passage_id") for c in citations if isinstance(c, dict)}
    mapping = item.get("distractor_evidence")
    if isinstance(mapping, dict):
        for entry in mapping.values():
            refs = entry.get("passage_ids") if isinstance(entry, dict) else None
            if not isinstance(refs, list):
                continue
            for pid in refs:
                source = sources.get(pid) if isinstance(pid, str) else None
                if source and pid not in cited and type(source.get("pdf_page_start")) is int:
                    citations.append({"passage_id": pid, "textbook_id": source["textbook_id"],
                                      "pdf_page": source["pdf_page_start"], "excerpt": source["excerpt"]})
                    cited.add(pid)
    for citation in citations:
        source = sources.get(citation.get("passage_id")) if isinstance(citation, dict) else None
        if (source and citation.get("textbook_id") == source.get("textbook_id")
                and citation.get("pdf_page") == source.get("pdf_page_start")
                and isinstance(citation.get("excerpt"), str) and citation["excerpt"]
                and citation["excerpt"] in source["excerpt"]):
            citation["printed_page_verified"] = False
            citation["edition"] = source.get("edition")
            citation["chapter"] = source.get("section_heading")
            citation["edition_status"] = "recorded_unverified" if source.get("edition") else "not_recorded"
    return item


def _repair_ellipsized_citations(draft, trusted_passages):
    """Replace only provably ordered, unique ellipsis spans with verbatim source text.

    Never repair a fabricated or ambiguous quote, change its source identity,
    or weaken reconciliation. The final citation must still pass reconcile().
    """
    import copy
    item = copy.deepcopy(draft)
    sources = {p["passage_id"]: p for p in trusted_passages}
    for citation in item.get("evidence", []):
        if not isinstance(citation, dict):
            continue
        quote = citation.get("excerpt")
        source = sources.get(citation.get("passage_id"))
        if not (isinstance(quote, str) and isinstance(source, dict)
                and citation.get("textbook_id") == source.get("textbook_id")
                and "..." in quote):
            continue
        parts = [part.strip() for part in quote.split("...")]
        if len(parts) != 2 or any(len(part) < 12 for part in parts):
            continue
        original = source["excerpt"]
        # Ambiguous fragments or reordered text are not safe to repair.
        if original.count(parts[0]) != 1 or original.count(parts[1]) != 1:
            continue
        start = original.index(parts[0])
        end_start = original.index(parts[1])
        end = end_start + len(parts[1])
        if end_start < start + len(parts[0]) or end - start > 1200:
            continue
        citation["excerpt"] = original[start:end]
    return item


def generate_one(adapter, *, mode, domain, section, objective, evidence,
                 format="MC", item_id, checkpoint=None, on_checkpoint=None,
                 generator_model_id=None, topic=None):
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
                objective=objective, evidence=evidence, topic=topic)
    if checkpoint is not None and (not isinstance(checkpoint, dict) or set(checkpoint) - {"concept_card", "draft"} or ("draft" in checkpoint and "concept_card" not in checkpoint)):
        raise ValueError("Invalid resume checkpoint")
    if on_checkpoint is not None and not callable(on_checkpoint):
        raise ValueError("Checkpoint writer must be callable")
    checkpoint = checkpoint or {}
    concept = checkpoint.get("concept_card") if "concept_card" in checkpoint else _response(adapter, build_step("concept_card", **args, format=format))
    # Some JSON-mode providers wrap the requested object under its step name.
    # Unwrap only the exact one-key envelope; never invent missing fields or IDs.
    if isinstance(concept, dict) and set(concept) == {"concept_card"} and isinstance(concept["concept_card"], dict):
        concept = concept["concept_card"]
    if not isinstance(concept, dict):
        raise ValueError("Concept card incomplete; draft generation blocked")
    concept = dict(concept)
    choice_plan = concept.pop("choice_plan", None)
    if choice_plan is not None:
        from item_mc_choice_plan_v2 import validate as validate_plan
        if format != "MC":
            raise ValueError("Concept card choice plan is MC-only")
        choice_plan = validate_plan(choice_plan)
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
        on_checkpoint("concept_card", {**concept, **({"choice_plan":choice_plan} if choice_plan is not None else {})})
    draft = checkpoint.get("draft") if "draft" in checkpoint else _response(adapter, build_step("item_draft", **args,
                                        format=format, concept_card=concept, choice_plan=choice_plan))
    if not isinstance(draft, dict):
        raise ValueError("Generated draft has wrong format or missing stem")
    if set(draft) == {"draft"} and isinstance(draft["draft"], dict):
        draft = draft["draft"]
    if draft.get("format") != format or not isinstance(draft.get("stem"), str):
        raise ValueError("Generated draft has wrong format or missing stem")
    planned_proposal = None
    if choice_plan is not None:
        from item_mc_choice_plan_v2 import bind
        planned_proposal = bind(choice_plan, draft)
        concept = {**concept, "counterfactual": _final_counterfactual(draft, planned_proposal)}
    if "draft" not in checkpoint and on_checkpoint is not None:
        on_checkpoint("draft", draft)
    rationale = _response(adapter, build_step("rationale", **args, format=format,
                                             concept_card=concept, draft=draft, choice_plan=choice_plan))
    if any(not rationale.get(field) for field in RATIONALE_FIELDS):
        raise ValueError("Rationale incomplete")
    if planned_proposal is not None and rationale.get("counterfactual_test") != planned_proposal:
        raise ValueError("Rationale incomplete: counterfactual differs from planned case")
    if format in ("MC", "MS") and "counterfactual_test" in rationale:
        concept = {**concept, "counterfactual": _final_counterfactual(draft, rationale["counterfactual_test"])}
        rationale = {k: rationale[k] for k in RATIONALE_FIELDS}
    # The model must not be allowed to overwrite identifiers, source, or approval.
    item = {**_complete_nonclinical_schema_fields(_repair_ellipsized_citations(_hydrate_indexed_citations(draft, evidence), evidence)), "item_id": item_id, "rules_version": "2.0",
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
