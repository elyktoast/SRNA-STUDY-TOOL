"""Bounded board-item checks. Independent screening never grants approval."""
import copy
import math
import re
from datetime import datetime, timezone
from nbcrna_taxonomy import SECTIONS, OBJECTIVES

DOMAINS = dict(zip(("I", "II", "III", "IV"), SECTIONS))
CRITERIA = {
    "blueprint": ("R-1.3", "objective"),
    "covered_options": ("R-4.2", "stem"),
    "context": ("R-4.3", "stem"),
    "counterfactual": ("R-5.3", "concept_card.counterfactual"),
    "trap": ("R-9", "rationale.trap"),
    "reasoning": ("R-1.3", "reasoning_level"),
    "distractors": ("R-6.1", "options"),
}


def classification(domain, section, objective):
    section = section.rsplit(".", 1)[-1]
    match = re.fullmatch(r"(I|II|III|IV)\.([A-Z])\.(\d+)", objective)
    if not match or match.group(1, 2) != (domain, section) or domain not in DOMAINS:
        raise ValueError("Invalid numbered blueprint objective")
    group = DOMAINS[domain]
    labels = OBJECTIVES.get(group, {}).get(section, [])
    number = int(match[3])
    if not 1 <= number <= len(labels):
        raise ValueError("Objective is not in the supported NBCRNA outline")
    return {"domain": domain, "section": section, "objective": objective,
            "section_label": SECTIONS[group][section], "objective_label": labels[number - 1]}


def obsolete_issues(item):
    # Evidence may faithfully contain an obsolete name. Only authored content is
    # subject to the writing ban; do not censor or modify indexed textbooks.
    if re.search(r"\b(?:historically|historical (?:case|practice|anesthe\w*|question|context|discussion|example|period))\b", str(item.get("stem", "")), re.I):
        return []
    values = [item.get("stem", ""), item.get("concept_card", {}),
              item.get("rationale", {}), item.get("distractor_evidence", {}),
              [o.get("text", "") for o in (item.get("options") if isinstance(item.get("options"), list) else []) if isinstance(o, dict)]]
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for key, child in value.items():
                if key not in ("passage_ids", "evidence_ids"):
                    yield from strings(child)
        elif isinstance(value, list):
            for child in value:
                yield from strings(child)
    return [{"rule_id": "R-8.4", "field": "content",
             "message": "Obsolete drug or test requires an explicitly historical item"}] if any(
        re.search(r"\b(?:halothane|ranitidine|bleeding\s+time)\b", text, re.I)
        for text in strings(values)) else []


def teaching_specificity_issues(item):
    """Necessary writing conditions, not proof of clinical or causal validity."""
    issues = []
    counterfactual = item.get("concept_card", {}).get("counterfactual", "")
    if not isinstance(counterfactual, str) or not re.search(
            r"\b(?:if|were|instead|versus|replac\w*|chang\w*)\b|\brather than\b", counterfactual, re.I):
        issues.append({"rule_id":"R-5.3", "field":"concept_card.counterfactual",
                       "message":"Counterfactual must explicitly state a changed condition, not restate the original answer"})
    if item.get("format") in ("MC", "MS"):
        trap = item.get("rationale", {}).get("trap", "")
        trap = trap if isinstance(trap, str) else ""
        wrong = [o for o in item.get("options", []) if isinstance(o, dict) and o.get("id") not in item.get("key", [])]
        labels = set(re.findall(r"\b(?:option|choice)\s+([A-F])\b", trap, re.I))
        names = " ".join(trap.casefold().split())
        if not any(o.get("id", "").upper() in {label.upper() for label in labels}
                   or (isinstance(o.get("text"), str) and len(o["text"].strip()) >= 3
                       and " ".join(o["text"].casefold().split()) in names) for o in wrong):
            issues.append({"rule_id":"R-9", "field":"rationale.trap",
                           "message":"Trap must identify a specific incorrect choice by option ID or full choice text"})
    return issues


def verify_counterfactual(item, proposal, reviewer):
    """Apply one explicit stem edit, then independently solve with the same options.

    The proposed changed answer never reaches the blind solver. Worded claims
    of validity cannot substitute for a different, uniquely solved answer.
    """
    issue = {"rule_id":"R-5.3", "field":"concept_card.counterfactual",
             "message":"Counterfactual must change a unique stem condition and independently yield a different correct answer"}
    if (not isinstance(proposal, dict) or set(proposal) != {"from_text", "to_text", "expected_key"}
            or any(not isinstance(proposal[k], str) or not 1 <= len(proposal[k]) <= 200 for k in ("from_text", "to_text"))
            or proposal["from_text"] == proposal["to_text"]
            or not isinstance(item.get("stem"), str) or item["stem"].count(proposal["from_text"]) != 1
            or proposal["from_text"].strip() == item["stem"].strip()):
        return {"status":"flag", "issues":[issue]}
    expected = proposal["expected_key"]
    normalize = lambda text: " ".join(text.casefold().split())
    statement = normalize(item.get("concept_card", {}).get("counterfactual", ""))
    if any(normalize(proposal[k]) not in statement for k in ("from_text", "to_text")):
        return {"status":"flag", "issues":[{**issue, "message":"The exact original condition and its replacement must both be stated in the concept-card counterfactual"}]}
    allowed = {o["id"] for o in item["options"]}
    if (not isinstance(expected, list) or len(expected) != len(item["key"])
            or any(not isinstance(k, str) or k not in allowed for k in expected)
            or len(set(expected)) != len(expected) or set(expected) == set(item["key"])):
        return {"status":"flag", "issues":[issue]}
    if not callable(reviewer):
        return {"status":"pending", "issues":[]}
    changed = copy.deepcopy(item)
    changed["stem"] = item["stem"].replace(proposal["from_text"], proposal["to_text"], 1)
    changed["key"] = expected
    from item_blind_review import payload
    from item_blind_review_scoring import compare
    try:
        response = reviewer(payload(changed))
        if (not isinstance(response, dict) or response.get("item_id") != changed.get("item_id")
                or not isinstance(response.get("key"), list)
                or any(not isinstance(k, str) or k not in allowed for k in response["key"])
                or len(set(response["key"])) != len(response["key"])):
            return {"status":"pending", "issues":[]}
        failed = compare(changed, response)
    except Exception:
        return {"status":"pending", "issues":[]}
    return {"status":"flag" if failed else "pass", "issues":[issue] if failed else [],
            "stem_change": {"from_text":proposal["from_text"], "to_text":proposal["to_text"]},
            "expected_key": expected, "independent_key": response.get("key") if isinstance(response, dict) else None}


def classification_mismatch_issues(item):
    """Conservative candidate conflicts FLAG review; no match proves nothing."""
    from nbcrna_classifier import suggest
    result = suggest(item.get("stem", ""))
    if result["status"] != "suggested":
        return []
    candidate = result["candidates"][0]
    code = next((code for code, name in DOMAINS.items() if name == candidate["domain"]), None)
    labels = OBJECTIVES.get(candidate["domain"], {}).get(candidate["section"], [])
    if code is None or candidate["objective"] not in labels:
        return []
    expected = f"{code}.{candidate['section']}.{labels.index(candidate['objective']) + 1}"
    if item.get("objective") != expected:
        return [{"rule_id":"R-1.3", "field":"objective",
                 "message":"Selected objective conflicts with an unambiguous stem-topic candidate; blueprint review required",
                 "candidate_objective":expected}]
    return []


def editorial(item, reviewer, *, counterfactual_reviewer=None, selected_topic=None):
    pending = {"status": "pending", "issues": [], "can_publish": False,
               "human_review_required": True, "clinical_truth_verified": False}
    local = teaching_specificity_issues(item) + classification_mismatch_issues(item)
    try:
        target = classification(item["domain"], item["section"], item["objective"])
        options = [{"id": o["id"], "text": o["text"]} for o in item.get("options", [])]
        response = reviewer({"step": "editorial_review", "rules_version": "2.0", "auto_publish": False,
            "independent": True, "classification": target, "format": item["format"],
            "selected_topic": selected_topic or target["objective_label"],
            "stem": item["stem"], "options": options, "reasoning_level": item["reasoning_level"],
            "teaching": {"misconception": item["concept_card"]["misconception"],
                         "counterfactual": item["concept_card"]["counterfactual"],
                         "trap": item["rationale"]["trap"]}})
        if (not isinstance(response, dict) or set(response) != {"checks", "findings", "counterfactual_test"}
                or not isinstance(response["checks"], dict) or set(response["checks"]) != set(CRITERIA)
                or any(v not in ("pass", "flag") for v in response["checks"].values())
                or not isinstance(response["findings"], list)):
            raise ValueError("Incomplete independent editorial review")
        findings = {}
        for f in response["findings"]:
            if (not isinstance(f, dict) or set(f) != {"criterion", "reason"}
                    or f["criterion"] not in CRITERIA or f["criterion"] in findings
                    or not isinstance(f["reason"], str) or not 1 <= len(f["reason"]) <= 300):
                raise ValueError("Invalid editorial finding")
            findings[f["criterion"]] = f["reason"]
        if set(findings) != {k for k, v in response["checks"].items() if v == "flag"}:
            raise ValueError("Editorial finding coverage mismatch")
        issues = [{"rule_id": CRITERIA[k][0], "field": CRITERIA[k][1], "message": v}
                  for k, v in findings.items()]
        model_rules = sorted({i["rule_id"] for i in issues})
        checks = dict(response["checks"])
        proof = {"status":"flag", "issues":[]} if checks["counterfactual"] == "flag" else verify_counterfactual(
            item, response["counterfactual_test"], counterfactual_reviewer)
        if checks["counterfactual"] == "pass":
            checks["counterfactual"] = proof["status"]
            issues.extend(proof["issues"])
        for issue in local:
            checks[{"R-5.3":"counterfactual", "R-9":"trap", "R-1.3":"blueprint"}[issue["rule_id"]]] = "flag"
        return {**pending, "status": "flag" if issues or local else "pending" if proof["status"] == "pending" else "pass", "issues": issues + local,
                "checks": checks, "model_flagged_rules": model_rules,
                "deterministic_rules": sorted({i["rule_id"] for i in local}), "model_status":"completed",
                "counterfactual_verification":proof}
    except Exception as exc:
        rule = getattr(exc, "rule", "REVIEW_RESPONSE_INVALID")
        allowed = {"PROVIDER_REQUEST_REJECTED", "PROVIDER_RATE_LIMIT", "PROVIDER_TIMEOUT", "PROVIDER_UPSTREAM", "PROVIDER_AUTH", "PROVIDER_FORBIDDEN"}
        messages = {"Incomplete independent editorial review", "Invalid editorial finding", "Editorial finding coverage mismatch"}
        return {**pending, "status":"flag" if local else "pending", "issues":local, "model_status":"pending",
                "deterministic_rules": sorted({i["rule_id"] for i in local}),
                "provider_rule": rule if rule in allowed else "REVIEW_RESPONSE_INVALID",
                "review_error": str(exc) if type(exc) is ValueError and str(exc) in messages else None}


def options_only(item, reviewer, *, shuffle=None):
    """Five fresh, independently shuffled, stem/key-free trials; p <= .05 flags.

    Chance is 1/C(n,k). A non-significant result is screening, not a claim that
    the item has no cue. Missing/invalid trials never become a pass.
    """
    pending = {"status": "pending", "issues": [], "can_publish": False,
               "human_review_required": True, "clinical_truth_verified": False}
    if item.get("format") not in ("MC", "MS"):
        return {**pending, "status": "not_applicable", "reason": "No answer options"}
    if shuffle is None:
        from secrets import SystemRandom
        shuffle = SystemRandom().shuffle
    hits, total, completed = 0, 5, 0
    try:
        original = item["options"]
        key = set(item["key"])
        for _ in range(total):
            permuted = copy.deepcopy(original)
            shuffle(permuted)
            binding = {chr(65 + i): option["id"] for i, option in enumerate(permuted)}
            response = reviewer({"step": "options_only_review", "rules_version": "2.0",
                "auto_publish": False, "independent": True, "format": item["format"],
                "select_count": len(key),
                "options": [{"id": chr(65 + i), "text": o["text"]} for i, o in enumerate(permuted)]})
            answer = response.get("key") if isinstance(response, dict) and set(response) == {"key"} else None
            if (not isinstance(answer, list) or len(answer) != len(key)
                    or any(not isinstance(k, str) or k not in binding for k in answer)
                    or len(set(answer)) != len(answer)):
                raise ValueError("Incomplete options-only trial")
            completed += 1
            hits += {binding[k] for k in answer} == key
        chance = 1 / math.comb(len(original), len(key))
        probability = sum(math.comb(total, k) * chance ** k * (1 - chance) ** (total - k)
                          for k in range(hits, total + 1))
        flagged = probability <= .05
        return {**pending, "status": "flag" if flagged else "pass", "trials": total,
                "key_guesses": hits, "chance_probability": chance,
                "binomial_tail_probability": probability,
                "issues": [{"rule_id": "R-12.2", "field": "options",
                    "message": "Options-only reviewer identified the key above chance in five shuffled trials"}] if flagged else []}
    except Exception:
        return {**pending, "completed_trials": completed}


def stamp_checks(item, screening):
    """Record server-observed checks, never model claims or human approval."""
    result = copy.deepcopy(item)
    if isinstance(result.get("options"), list) and isinstance(result.get("key"), list):
        for option in result["options"]:
            if isinstance(option, dict) and option.get("id") in result["key"]:
                option["error_pattern"] = None
    stage_rules = {"schema": ["R-15"], "deterministic_text": ["R-6.8", "R-6.10", "R-2.8", "R-8.4"],
        "blind_model": ["R-12.1"], "explanation_evidence": ["R-2.4"],
        "independent_option_evidence": ["R-2.1", "R-2.4"], "duplicates": ["R-12.9"],
        "editorial_quality": [v[0] for v in CRITERIA.values()], "options_only": ["R-12.2"]}
    statuses = {}
    for name, rules in stage_rules.items():
        stage = screening.get("stages", {}).get(name, {})
        state = stage.get("status", "pending")
        if name == "editorial_quality":
            for criterion, (rule, _) in CRITERIA.items():
                statuses.setdefault(rule, []).append(stage.get("checks", {}).get(criterion, "pending"))
        else:
            for rule in rules:
                statuses.setdefault(rule, []).append(state)
        for issue in stage.get("issues", []):
            if isinstance(issue, dict) and issue.get("rule_id"):
                statuses.setdefault(issue["rule_id"], []).append("flag")
    values = {rule: "fail" if any(s in ("flag", "fail") for s in states)
              else "pass" if all(s == "pass" for s in states) else "pending"
              for rule, states in statuses.items()}
    original = {i["rule_id"] for i in screening.get("rewrite_original_issues", []) if isinstance(i, dict) and i.get("rule_id")}
    result["self_check"] = {"rules_checked": sorted(r for r, s in values.items() if s != "pending"),
        "rule_results": values, "failed_then_fixed": sorted(r for r in original if values.get(r) == "pass"),
        "blind_solve": values.get("R-12.1", "pending"), "recorded_by": "trusted_screening",
        "human_approved": False}
    result["stats"] = {"n_responses": 0, "p_value": None, "point_biserial": None, "distractor_pct": {}}
    result.setdefault("audit", []).append({"who": "automated_screening", "what_changed": "Recorded actual screening results; no human approval",
        "date": datetime.now(timezone.utc).date().isoformat()})
    return result
