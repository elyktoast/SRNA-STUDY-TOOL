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
        # Matching labels may be plain strings or ID/text objects.
        # Strip every other field, including keyed pairs and explanations.
        def blind_labels(entries):
            if not isinstance(entries, list):
                raise ValueError("Matching labels required")
            sanitized = []
            for entry in entries:
                if isinstance(entry, str):
                    sanitized.append(entry)
                elif isinstance(entry, dict):
                    sanitized.append({"id": entry["id"], "text": entry["text"]})
                else:
                    raise ValueError("Invalid matching label")
            return sanitized
        data["left"] = blind_labels(dd.get("left"))
        data["right"] = blind_labels(dd.get("right"))
    elif fmt == "HS":
        hs = item.get("hs") or {}
        figure = hs.get("figure")
        # Never forward nested region answers or provenance to a blind model.
        if isinstance(figure, dict):
            figure = {k: figure[k] for k in ("url", "alt", "width", "height") if k in figure}
        data["figure"] = figure
    return data


def compare(item, response):
    if not isinstance(response, dict) or response.get("item_id") != item.get("item_id"):
        return [{"rule_id": "R-12.1", "message": "Independent blind response missing or mismatched"}]
    if item.get("format") in ("MC", "MS"):
        chosen = response.get("key")
        expected = item.get("key")
        if (not isinstance(chosen, list) or not isinstance(expected, list)
                or not all(isinstance(v, str) for v in chosen + expected)
                or len(chosen) != len(set(chosen))
                or set(chosen) != set(expected)):
            return [{"rule_id": "R-12.1", "message": "Blind solve disagrees with keyed response"}]
        return []
    return [{"rule_id": "R-12.1", "message": "Format-specific blind scoring not yet implemented"}]
