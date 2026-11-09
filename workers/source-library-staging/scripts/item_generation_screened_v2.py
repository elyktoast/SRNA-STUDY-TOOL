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
                        semantic_lookup=None, review_repair=None, _verified_candidate=None, topic=None, explanation_review=None, quality_review=None):
    if blind_reviewer is not None and (not callable(blind_reviewer) or not isinstance(generator_model_id, str) or not isinstance(reviewer_model_id, str) or not generator_model_id.strip() or not reviewer_model_id.strip() or generator_model_id.strip() == reviewer_model_id.strip()):
        raise ValueError("Independent reviewer requires distinct verified model identities")
    if semantic_lookup is not None and (not callable(semantic_lookup) or embedding is not None or neighbors is not None):
        raise ValueError("Use either trusted semantic lookup or supplied vectors")
    if (embedding is None) != (neighbors is None):
        raise ValueError("Semantic screening requires both candidate embedding and neighbors")
    generated = ({"item": _verified_candidate, "schema_issues": []}
                 if _verified_candidate is not None else generate_one(adapter, mode=mode, domain=domain,
                             section=section, objective=objective,
                             evidence=evidence, format=format, item_id=item_id,
                             checkpoint=checkpoint, on_checkpoint=on_checkpoint,
                             generator_model_id=generator_model_id, topic=topic))
    # Collect inexpensive editorial issues before spending the only rewrite on
    # a schema/source defect; otherwise an already-visible length cue could be
    # discovered only after that budget has been exhausted.
    if rewrite is not None and generated["schema_issues"]:
        from item_text_checks import check as check_text
        editorial = check_text(generated["item"], source_texts=[p["excerpt"] for p in evidence])
        generated["schema_issues"] = generated["schema_issues"] + [
            issue for issue in editorial if issue not in generated["schema_issues"]]
    rewrite_attempts = 0
    rewrite_original_issues = list(generated["schema_issues"])
    if rewrite is not None and generated["schema_issues"]:
        def validate_rewrite(candidate):
            problems = validate_complete_item(candidate)
            problems.extend(reconcile(candidate, evidence))
            problems.extend(answer_evidence_check(candidate, evidence)
                            if format in ("MC", "MS")
                            else special_evidence_check(candidate, evidence))
            from item_text_checks import check as check_text
            problems.extend(check_text(candidate, source_texts=[p["excerpt"] for p in evidence]))
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
        if explanation_review is not None:
            stages["explanation_evidence"] = {"status":"pending", "issues":[], "blocked_by":"schema"}
        for name in ("deterministic_text", "math", "duplicates", "blind_model"):
            stages[name]["blocked_by"] = "schema"
            stages[name]["reason"] = "Generation validation failed; downstream screening not run"
        if not source_failure:
            stages["evidence"]["blocked_by"] = "schema"
            stages["evidence"]["reason"] = "Generation validation failed; downstream screening not run"
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
                              "rewrite_attempts_used": rewrite_attempts,
                              "rewrite_original_issues": rewrite_original_issues if rewrite_attempts else [],
                              "rewrite_revised_issues": issues if rewrite_attempts else []}, "next_state": state,
                "requires_human_review": True, "can_publish": False,
                "database_writes": False, "rewrite_attempts_used": rewrite_attempts}
    semantic_lookup_failed = False
    semantic_lookup_reason = None
    if semantic_lookup is not None:
        try:
            pair = semantic_lookup(generated["item"])
            if (not isinstance(pair, dict) or set(pair) != {"embedding", "neighbors", "search_complete", "index_id"}
                    or pair["search_complete"] is not True
                    or not isinstance(pair["index_id"], str) or not pair["index_id"].strip()):
                raise ValueError("Unverified semantic lookup result")
            embedding, neighbors = pair["embedding"], pair["neighbors"]
            if embedding is None or not isinstance(neighbors, list):
                raise ValueError("Incomplete semantic lookup")
            from item_semantic_duplicates import screen as verify_semantic_vectors
            verify_semantic_vectors(embedding, neighbors)
        except Exception as exc:
            embedding, neighbors = None, None
            semantic_lookup_failed = True
            semantic_lookup_reason = (
                str(exc) if isinstance(exc, ValueError) and str(exc) in (
                    "Semantic index not verified",
                    "Complete canonical item inventory required",
                    "Complete canonical stem hashes required",
                    "Semantic index coverage does not match canonical item inventory",
                    "Stale semantic index stem hash",
                    "Unverified semantic lookup result",
                    "Incomplete semantic lookup",
                ) else "Semantic index lookup failed or returned unverified coverage"
            )
    indexed = {p["passage_id"]: {
        "passage_id": p["passage_id"], "textbook_id": p["textbook_id"],
        "pdf_page": p.get("pdf_page_start"), "text": p["excerpt"]}
        for p in evidence}
    review = intake({"questions": [generated["item"]]},
                    passages=indexed, known_stems=known_stems,
                    source_texts=[p["excerpt"] for p in evidence],
                    calculations={item_id: calculation} if calculation is not None else None,
                    embeddings={item_id: embedding} if embedding is not None else None,
                    neighbors=neighbors)
    result = review["draft_reviews"][0]
    screening = result["screening"]
    if semantic_lookup_failed or (semantic_lookup is None and embedding is None):
        # A stem-only or absent-index check is not an exhaustive semantic search.
        screening["stages"]["duplicates"] = {
            "status": "pending", "issues": [],
            "reason": semantic_lookup_reason or "Semantic index not supplied; exact-stem check is insufficient"
        }
        screening["screening_complete"] = False
    screening["rewrite_attempts_used"] = rewrite_attempts
    screening["rewrite_original_issues"] = rewrite_original_issues if rewrite_attempts else []
    screening["rewrite_revised_issues"] = generated["schema_issues"] if rewrite_attempts else []
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
            try:
                screening = attach_blind(screening, blind)
            except (ValueError, TypeError, KeyError):
                # Invalid reviewer metadata must never be treated as a pass.
                screening["stages"]["blind_model"] = {
                    "status": "pending", "issues": []}
                screening["screening_complete"] = False
            else:
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
    explanation_report = None
    if explanation_review is not None:
        try:
            explanation_report = explanation_review(generated["item"])
            if (not isinstance(explanation_report, dict)
                    or explanation_report.get("status") not in ("pass", "flag", "pending")
                    or not isinstance(explanation_report.get("issues"), list)
                    or explanation_report.get("can_publish") is not False
                    or explanation_report.get("clinical_truth_verified") is not False
                    or explanation_report.get("human_review_required") is not True
                    or (explanation_report["status"] == "flag") != bool(explanation_report["issues"])):
                raise ValueError("Invalid explanatory review")
        except Exception:
            explanation_report = {"status":"pending", "issues":[], "can_publish":False,
                                  "clinical_truth_verified":False,"human_review_required":True}
        screening["stages"]["explanation_evidence"] = explanation_report
        if explanation_report["status"] != "pass":
            screening["screening_complete"] = False
            next_state = "needs_source_review"
        if explanation_report["status"] == "pending":
            screening.setdefault("pending_verifications", []).append("explanation_evidence")
    quality_issues = []
    if quality_review is not None:
        names = ("editorial_quality", "options_only")
        try:
            reports = quality_review(generated["item"])
            if not isinstance(reports, dict) or set(reports) != set(names):
                raise ValueError("Incomplete board quality review")
            for name, report in reports.items():
                if (not isinstance(report, dict) or report.get("status") not in ("pass", "flag", "pending", "not_applicable")
                        or not isinstance(report.get("issues"), list) or report.get("can_publish") is not False
                        or report.get("human_review_required") is not True
                        or report.get("clinical_truth_verified") is not False
                        or (report["status"] == "flag") != bool(report["issues"])
                        or (report["status"] == "not_applicable" and (name != "options_only" or format in ("MC", "MS")))):
                    raise ValueError("Untrusted board quality report")
        except Exception:
            reports = {name: {"status":"pending", "issues":[], "can_publish":False,
                "human_review_required":True, "clinical_truth_verified":False} for name in names}
        for name, report in reports.items():
            screening["stages"][name] = report
            if report["status"] in ("pending", "flag"):
                screening["screening_complete"] = False
                if next_state != "needs_source_review":
                    next_state = "needs_editorial_review"
            if report["status"] == "pending":
                screening.setdefault("pending_verifications", []).append(name)
            quality_issues.extend(report["issues"])
    screening["next_state"] = next_state
    # A failed independent or deterministic screening may trigger one bounded
    # repair. Never retry on missing verification (pending) or provider outages.
    # Re-run the COMPLETE screening after repair; old passes cannot be inherited.
    if review_repair is not None and _verified_candidate is None and not rewrite_attempts:
        failed = []
        for stage_name, stage in screening.get("stages", {}).items():
            if stage_name == "human_review" or not isinstance(stage, dict):
                continue
            if stage.get("status") in ("fail", "flag"):
                for issue in stage.get("issues", []):
                    if isinstance(issue, dict) and issue.get("rule_id"):
                        failed.append(issue)
        if failed:
            def verify(candidate):
                problems = validate_complete_item(candidate)
                problems.extend(reconcile(candidate, evidence))
                problems.extend(answer_evidence_check(candidate, evidence)
                                if format in ("MC", "MS")
                                else special_evidence_check(candidate, evidence))
                return problems
            repaired = attempt_once(generated["item"], failed, review_repair, verify)
            if not repaired["issues"] and repaired["rewrite_attempts"] == 1:
                rerun = generate_and_screen(
                    adapter, mode=mode, domain=domain, section=section,
                    objective=objective, evidence=evidence, format=format,
                    item_id=item_id, known_stems=known_stems,
                    calculation=calculation, embedding=embedding,
                    neighbors=neighbors, blind_reviewer=blind_reviewer,
                    generator_model_id=generator_model_id,
                    reviewer_model_id=reviewer_model_id,
                    semantic_lookup=semantic_lookup,
                    _verified_candidate=repaired["item"], topic=topic, explanation_review=explanation_review, quality_review=quality_review)
                rerun["rewrite_attempts_used"] = 1
                rerun["screening"]["rewrite_attempts_used"] = 1
                rerun["screening"]["rewrite_attempts_allowed"] = 0
                rerun["screening"]["rewrite_original_issues"] = failed
                return rerun
            screening["rewrite_attempts_used"] = 1
            screening["rewrite_attempts_allowed"] = 0
            screening["rewrite_original_issues"] = failed
            screening["rewrite_revised_issues"] = repaired["issues"]
            return {"item_id": item_id, "item": generated["item"],
                    "generator_issues": failed, "screening": screening,
                    "next_state": "needs_editorial_review",
                    "requires_human_review": True, "can_publish": False,
                    "database_writes": False, "rewrite_attempts_used": 1}
    return {"item_id": item_id, "item": generated["item"],
            "generator_issues": (explanation_report["issues"] if explanation_report is not None else []) + quality_issues, "screening": screening,
            "next_state": next_state, "requires_human_review": True,
            "can_publish": False, "database_writes": False,
            "rewrite_attempts_used": rewrite_attempts}
