"""Trusted staging handoff from generated draft to read-only screening.

Never publishes or persists drafts. Missing verification inputs remain pending.
"""
from item_generation_runner_v2 import generate_one
from item_draft_intake import intake
from item_independent_blind_v2 import review as blind_review
from item_screening_blind_handoff_v2 import attach as attach_blind
from item_rewrite_once_v2 import attempt_once
from item_generation_contract_v2 import validate_complete_item
from item_source_reconciliation_v2 import reconcile
from item_answer_evidence_v2 import check as answer_evidence_check
from item_special_format_evidence_v2 import check as special_evidence_check

def generate_and_screen(adapter, *, mode, domain, section, objective, evidence,
                        format="MC", item_id, known_stems=(), calculation=None,
                        embedding=None, neighbors=None, blind_reviewer=None,
                        generator_model_id=None, reviewer_model_id=None,
                        checkpoint=None, on_checkpoint=None, rewrite=None,
                        semantic_lookup=None):
    if blind_reviewer is not None and (not callable(blind_reviewer) or not generator_model_id or not reviewer_model_id or generator_model_id == reviewer_model_id):
        raise ValueError("Independent reviewer requires distinct verified model identities")
    if semantic_lookup is not None and (not callable(semantic_lookup) or embedding is not None or neighbors is not None):
        raise ValueError("Use either trusted semantic lookup or supplied vectors")
    if (embedding is None) != (neighbors is None):
        raise ValueError("Semantic screening requires both candidate embedding and neighbors")
    generated = generate_one(adapter, mode=mode, domain=domain,
                             section=section, objective=objective,
                             evidence=evidence, format=format, item_id=item_id,
                             checkpoint=checkpoint, on_checkpoint=on_checkpoint,
                             generator_model_id=generator_model_id)
    rewrite_attempts = 0
    if rewrite is not None and generated["schema_issues"]:
        def validate_rewrite(candidate):
            problems = validate_complete_item(candidate)
            problems.extend(reconcile(candidate, evidence))
            problems.extend(answer_evidence_check(candidate, evidence)
                            if format in ("MC", "MS")
                            else special_evidence_check(candidate, evidence))
            return problems
        repaired = attempt_once(generated["item"], generated["schema_issues"],
                                rewrite, validate_rewrite)
        rewrite_attempts = repaired["rewrite_attempts"]
        generated = {**generated, "item": repaired["item"],
                     "schema_issues": repaired["issues"],
                     "rewrite_attempts": repaired["rewrite_attempts"]}
    if generated["schema_issues"]:
        issues = generated["schema_issues"]
        source_failure = any(x["rule_id"] in ("R-2.5", "R-17") for x in issues)
        state = "needs_source_review" if source_failure else "needs_editorial_review"
        pending = ("schema", "deterministic_text", "math", "evidence",
                   "duplicates", "blind_model", "human_review")
        stages = {name: {"status": "pending", "issues": []} for name in pending}
        stages["schema"] = {"status": "fail", "issues": issues}
        if source_failure:
            stages["evidence"] = {"status": "fail",
                                  "issues": [x for x in issues if x["rule_id"] in ("R-2.5", "R-17")]}
        remaining = [name for name, stage in stages.items()
                     if stage["status"] == "pending" and name != "human_review"]
        return {"item_id": item_id, "item": generated["item"],
                "generator_issues": issues,
                "screening": {"can_publish": False, "screening_complete": False,
                              "next_state": state, "stages": stages,
                              "pending_verifications": remaining,
                              "rewrite_attempts_allowed": 1 - rewrite_attempts,
                              "rewrite_attempts_used": rewrite_attempts}, "next_state": state,
                "requires_human_review": True, "can_publish": False,
                "database_writes": False, "rewrite_attempts_used": rewrite_attempts}
    semantic_lookup_failed = False
    if semantic_lookup is not None:
        try:
            pair = semantic_lookup(generated["item"])
            if not isinstance(pair, dict) or set(pair) != {"embedding", "neighbors"}:
                raise ValueError("Invalid semantic lookup result")
            embedding, neighbors = pair["embedding"], pair["neighbors"]
            if embedding is None or not isinstance(neighbors, list):
                raise ValueError("Incomplete semantic lookup")
        except Exception:
            embedding, neighbors = None, None
            semantic_lookup_failed = True
    indexed = {p["passage_id"]: {
        "passage_id": p["passage_id"], "textbook_id": p["textbook_id"],
        "pdf_page_start": p.get("pdf_page_start"), "text": p["excerpt"]}
        for p in evidence}
    review = intake({"questions": [generated["item"]]},
                    passages=indexed, known_stems=known_stems,
                    source_texts=[p["excerpt"] for p in evidence],
                    calculations={item_id: calculation} if calculation is not None else None,
                    embeddings={item_id: embedding} if embedding is not None else None,
                    neighbors=neighbors)
    result = review["draft_reviews"][0]
    screening = result["screening"]
    if semantic_lookup_failed:
        screening["stages"]["duplicates"] = {"status": "pending", "issues": []}
        screening["screening_complete"] = False
    screening["rewrite_attempts_used"] = rewrite_attempts
    screening["rewrite_attempts_allowed"] = 1 - rewrite_attempts
    next_state = result["status"]
    pending = [name for name in ("schema", "deterministic_text", "math", "evidence",
                                "duplicates", "blind_model")
               if screening.get("stages", {}).get(name, {}).get("status") == "pending"]
    if pending:
        screening["screening_complete"] = False
        screening["pending_verifications"] = pending
    if blind_reviewer is not None:
        try:
            blind = blind_review(generated["item"], blind_reviewer,
                                 generator_model_id=generator_model_id,
                                 reviewer_model_id=reviewer_model_id)
        except Exception:
            # A provider outage must not discard the generated draft or
            # incorrectly mark independent verification as complete.
            screening["stages"]["blind_model"] = {
                "status": "pending", "issues": []}
            screening["screening_complete"] = False
        else:
            screening = attach_blind(screening, blind)
            next_state = screening.get("next_state", next_state)
        screening.pop("pending_verifications", None)
        pending = [name for name in ("schema", "deterministic_text", "math",
                                    "evidence", "duplicates", "blind_model")
                   if screening.get("stages", {}).get(name, {}).get("status") == "pending"]
        if pending:
            screening["pending_verifications"] = pending
            screening["screening_complete"] = False
        else:
            screening.pop("pending_verifications", None)
    if screening.get("stages", {}).get("duplicates", {}).get("status") == "flag" and next_state == "draft":
        next_state = "needs_editorial_review"
    screening["next_state"] = next_state
    return {"item_id": item_id, "item": generated["item"],
            "generator_issues": [], "screening": screening,
            "next_state": next_state, "requires_human_review": True,
            "can_publish": False, "database_writes": False,
            "rewrite_attempts_used": rewrite_attempts}
