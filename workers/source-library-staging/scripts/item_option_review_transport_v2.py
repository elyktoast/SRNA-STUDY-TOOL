"""Recover a rejected oversized MC review by submitting its evidence per choice."""
from item_ai_https_transport_v2 import TransportError


def request_judgments(payload, call):
    request = {**payload, "step": "option_review", "blind": True,
               "rules_version": "2.0", "auto_publish": False}
    try:
        return call(request)
    except TransportError as exc:
        if exc.rule != "PROVIDER_REQUEST_SIZE" or payload.get("format") != "MC":
            raise
    # A size rejection yields no clinical judgment. Keep the same stem and all
    # choices visible, but send only the target option's independently found
    # passages. Valid judgments are never retried.
    judgments = []
    for audit in payload["retrieval"]["option_audits"]:
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
        judgments.extend(result["judgments"])
    return {"judgments": judgments}
