"""Optional independent option adjudication handoff; no provider transport.

A validated reviewer report remains subject to clinical human review.
"""
from item_option_adjudication_v2 import evaluate
import re
import unicodedata


def _paired_component_words(item):
    """Recognize shared labelled pairs, not arbitrary prose or clinical truth."""
    words = lambda text: set(re.findall(r"[^\W\d_]+", unicodedata.normalize("NFKC", text).casefold()))
    pairs = []
    for option in item.get("options", []):
        parts = option.get("text", "").split(";")
        if len(parts) != 2:
            return []
        labels = [re.fullmatch(r"\s*([^:]{1,80}):\s*\S.*", part) for part in parts]
        if not all(labels):
            return []
        pairs.append([words(label[1]) for label in labels])
    return pairs[0] if pairs and all(pair == pairs[0] for pair in pairs) and all(pairs[0]) else []


def run(item, retrieval, reviewer, *, source_passages, generator_model_id, reviewer_model_id, require_quotes=False):
    if not callable(reviewer):
        raise ValueError("Independent option reviewer adapter required")
    if (not isinstance(generator_model_id, str) or not generator_model_id.strip()
            or not isinstance(reviewer_model_id, str) or not reviewer_model_id.strip()
            or generator_model_id.strip() == reviewer_model_id.strip()):
        raise ValueError("Distinct generator and reviewer model identities required")
    if (not isinstance(retrieval, dict) or retrieval.get("all_options_searched") is not True
            or retrieval.get("all_options_have_matches") is False):
        return {"status": "pending", "issues": [{"rule_id": "R-12.4",
                "message": "Independent option retrieval incomplete"}],
                "clinical_truth_verified": False, "can_publish": False}
    if not isinstance(source_passages, list):
        raise ValueError("Trusted independently retrieved source passages required")
    indexed = {p.get("passage_id"): p for p in source_passages
               if isinstance(p, dict) and isinstance(p.get("passage_id"), str)
               and isinstance(p.get("excerpt"), str) and p["excerpt"].strip()}
    referenced = {pid for a in retrieval.get("option_audits", [])
                  for pid in a.get("retrieved_passage_ids", [])}
    if not referenced or not referenced.issubset(indexed):
        return {"status": "pending", "issues": [{"rule_id": "R-12.4",
                "message": "Independent source passage text unavailable"}],
                "clinical_truth_verified": False, "can_publish": False}
    # Pass a restricted request: the reviewer must return source-grounded
    # judgments, and the caller must provide authenticated source access.
    # Do not disclose the keyed answer or expected verdict to the independent
    # reviewer. The trusted evaluator compares its blind judgment afterward.
    blind_retrieval = {"option_audits": [
        {"option_id": a["option_id"],
         "retrieved_passage_ids": a["retrieved_passage_ids"]}
        for a in retrieval["option_audits"]]}
    request = {"format": item.get("format"), "stem": item.get("stem"), "options": [{"id": o["id"], "text": o["text"]}
                           for o in item.get("options", [])],
               "retrieval": blind_retrieval,
               "source_passages": [indexed[pid] for pid in sorted(referenced)],
               "task": "independent_option_adjudication"}
    try:
        response = reviewer(request)
        report = evaluate(item, retrieval, response)
        if require_quotes:
            components = _paired_component_words(item)
            for judgment in response:
                explanation = judgment.get("explanation", "")
                if isinstance(explanation, str) and any(x in explanation.casefold() for x in
                    ("does not mention", "not mentioned", "no mention", "not discussed", "does not endorse")):
                    report["issues"].append({"rule_id": "R-12.4", "option_id": judgment.get("option_id"),
                                             "message": "Independent review relies on source silence"})
                quotes = judgment.get("quotes")
                refs = judgment.get("passage_ids", [])
                if (not isinstance(quotes, list) or not 1 <= len(quotes) <= 8
                        or any(not isinstance(quote, str) or not 6 <= len(quote) <= 300
                               or not any(pid in indexed and quote in indexed[pid]["excerpt"] for pid in refs)
                               for quote in quotes)):
                    report["issues"].append({"rule_id": "R-12.4", "option_id": judgment.get("option_id"),
                                             "message": "Independent reviewer quote is not verbatim indexed evidence"})
                if components and judgment.get("verdict") == "supports_key" and isinstance(quotes, list):
                    quoted_words = set(re.findall(r"[^\W\d_]+", unicodedata.normalize("NFKC", " ".join(
                        quote for quote in quotes if isinstance(quote, str))).casefold()))
                    # Necessary coverage only. Mentioning both components never
                    # proves their states; the independent clinical judgment and
                    # full explanatory source review remain mandatory.
                    if any(not component.issubset(quoted_words) for component in components):
                        report["issues"].append({"rule_id":"R-12.4", "option_id":judgment.get("option_id"),
                            "message":"Independent key evidence omits a paired response component"})
            if report["issues"]:
                report["status"] = "pending"
        report["judgments"] = [{k: j[k] for k in
            ("option_id", "verdict", "passage_ids", "quotes", "explanation", "source_conflict_found", "contradiction_found") if k in j}
            for j in response]
    except Exception as exc:
        rule = getattr(exc, "rule", "REVIEW_RESPONSE_INVALID")
        allowed = {"PROVIDER_RATE_LIMIT", "PROVIDER_TIMEOUT", "PROVIDER_UPSTREAM", "PROVIDER_RESPONSE", "PROVIDER_AUTH", "PROVIDER_FORBIDDEN", "PROVIDER_NETWORK", "REVIEW_RESPONSE_INVALID"}
        rule = rule if rule in allowed else "REVIEW_RESPONSE_INVALID"
        return {"status": "pending", "provider_rule": rule, "issues": [{"rule_id": "R-12.4",
                "message": "Independent option adjudication unavailable or invalid"}],
                "clinical_truth_verified": False, "can_publish": False}
    return {**report, "generator_model_id": generator_model_id,
            "reviewer_model_id": reviewer_model_id,
            "can_publish": False}
