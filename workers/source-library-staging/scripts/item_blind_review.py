"""Prepare independent blind screening without exposing the answer or rationale.

The blind reviewer must be a separate model/service; this module only
constructs a sanitized payload and compares its response.
"""
def payload(item):
    fmt = item.get("format")
    data = {"item_id": item.get("item_id"), "format": fmt,
            "stem": item.get("stem")}
    if fmt in ("MC", "MS"):
        data["options"] = [{"id": o["id"], "text": o["text"]}
                           for o in item.get("options", [])]
        if fmt == "MS":
            data["select_count"] = item.get("select_count")
    elif fmt == "SA":
        sa = item.get("sa") or {}
        data["unit"] = sa.get("unit")
        data["rounding"] = sa.get("rounding")
    elif fmt == "DD":
        dd = item.get("dd") or {}
        data["left"] = dd.get("left")
        data["right"] = dd.get("right")
    elif fmt == "HS":
        hs = item.get("hs") or {}
        data["figure"] = hs.get("figure")
    return data


def compare(item, response):
    if not isinstance(response, dict) or response.get("item_id") != item.get("item_id"):
        return [{"rule_id": "R-12.1", "message": "Independent blind response missing or mismatched"}]
    if item.get("format") in ("MC", "MS"):
        chosen = response.get("key")
        expected = item.get("key")
        if not isinstance(chosen, list) or not isinstance(expected, list) or set(chosen) != set(expected):
            return [{"rule_id": "R-12.1", "message": "Blind solve disagrees with keyed response"}]
        return []
    return [{"rule_id": "R-12.1", "message": "Format-specific blind scoring not yet implemented"}]
