"""Recover a rejected or structurally invalid MC review in per-choice requests."""
from concurrent.futures import ThreadPoolExecutor

from item_ai_https_transport_v2 import TransportError


def request_judgments(payload, call, *, parallel=False):
    request = {**payload, "step": "option_review", "blind": True,
               "rules_version": "2.0", "auto_publish": False}
    try:
        return call(request)
    except TransportError as exc:
        if exc.rule != "PROVIDER_REQUEST_SIZE" or payload.get("format") != "MC":
            raise
    except ValueError as exc:
        if payload.get("format") != "MC" or str(exc) not in {
                "Independent judgments required", "Invalid independent judgment map"}:
            raise
    # A size rejection or unusable map yields no validated clinical judgment. Keep the same stem and all
    # choices visible, but send only the target option's independently found
    # passages. Valid judgments are never retried.
    def judge(audit):
        target = audit["option_id"]
        allowed = set(audit["retrieved_passage_ids"])
        result = call({**request, "target_option": target,
                       "retrieval": {"option_audits": [audit]},
                       "source_passages": [p for p in payload["source_passages"]
                                           if p["passage_id"] in allowed]})
        if (set(result) != {"judgments"} or not isinstance(result["judgments"], list)
                or len(result["judgments"]) != 1
                or result["judgments"][0].get("option_id") != target):
            raise ValueError("Invalid independent judgment map")
        return result["judgments"][0]

    audits = payload["retrieval"]["option_audits"]
    if parallel:
        with ThreadPoolExecutor(max_workers=2) as pool:
            judgments = []
            for start in range(0, len(audits), 2):
                judgments.extend(pool.map(judge, audits[start:start + 2]))
    else:
        judgments = [judge(audit) for audit in audits]
    return {"judgments": judgments}
