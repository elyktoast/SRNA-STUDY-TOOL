"""Blind-review comparison for v2.0 formats, without model invocation.

Human review still required. DD pairs use canonical left/right identifiers.
Hotspot compares named regions, not untrusted pixel guesses.
"""
import math


def compare(item, response):
    if not isinstance(response, dict) or response.get("item_id") != item.get("item_id"):
        return [{"rule_id": "R-12.1", "message": "Missing or mismatched blind response"}]
    kind = item.get("format")
    if kind in ("MC", "MS"):
        key = item.get("key")
        chosen = response.get("key")
        if (not isinstance(key, list) or not isinstance(chosen, list)
                or not all(isinstance(x, str) for x in key + chosen)
                or len(chosen) != len(set(chosen)) or set(chosen) != set(key)):
            issue = {"rule_id": "R-12.1", "message": "Blind selection disagrees"}
            # Diagnostics go only to trusted screening/repair, never the blind
            # request. Do not echo malformed or arbitrary provider content.
            options = item.get("options")
            ids = {o["id"] for o in options if isinstance(o, dict) and isinstance(o.get("id"), str)} if isinstance(options, list) else set()
            if (kind == "MC" and isinstance(key, list) and isinstance(chosen, list)
                    and len(key) == 1 and len(chosen) <= 4
                    and all(isinstance(v, str) and v in ids and v in "ABCD" and len(v) == 1 for v in key + chosen)
                    and len(key) == len(set(key)) and len(chosen) == len(set(chosen))):
                issue.update(expected_key=list(key), independent_key=list(chosen))
            return [issue]
    elif kind == "SA":
        sa = item.get("sa") or {}
        value = response.get("numeric_answer")
        if type(value) not in (int, float) or not math.isfinite(value) or type(sa.get("answer")) not in (int, float) or type(sa.get("tolerance")) not in (int, float):
            return [{"rule_id": "R-12.1", "message": "Invalid numeric blind response"}]
        if abs(value - sa["answer"]) > sa["tolerance"]:
            return [{"rule_id": "R-12.1", "message": "Blind numeric result disagrees"}]
    elif kind == "DD":
        pairs = (item.get("dd") or {}).get("pairs")
        if not isinstance(pairs, dict) or response.get("pairs") != pairs:
            return [{"rule_id": "R-12.1", "message": "Blind matching disagrees"}]
    elif kind == "HS":
        correct = (item.get("hs") or {}).get("correct_region")
        if not correct or response.get("region") != correct:
            return [{"rule_id": "R-12.1", "message": "Blind hotspot disagrees"}]
    else:
        return [{"rule_id": "R-12.1", "message": "Unsupported blind-review format"}]
    return []
