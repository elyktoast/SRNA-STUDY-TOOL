"""Evidence traceability for numeric, matching and hotspot v2 items.

This validates indexed source references and per-component explanations, NOT
clinical correctness, arithmetic recomputation or licensed image authenticity.
"""
def check(item, trusted_passages):
    if not isinstance(item, dict) or not isinstance(trusted_passages, list):
        raise ValueError("Item and trusted evidence required")
    fmt = item.get("format")
    if fmt not in ("SA", "DD", "HS"):
        return [{"rule_id": "R-12.4", "message": "Unsupported special format"}]
    indexed = {p["passage_id"] for p in trusted_passages
               if isinstance(p, dict) and p.get("passage_id") and p.get("excerpt")}
    mapping = item.get("distractor_evidence")
    if not isinstance(mapping, dict):
        return [{"rule_id": "R-12.4", "message": "Component evidence map required"}]
    if fmt == "SA":
        required = {"solution"}
    elif fmt == "DD":
        dd = item.get("dd")
        pairs = dd.get("pairs") if isinstance(dd, dict) else None
        if not isinstance(pairs, dict) or len(pairs) != 4:
            return [{"rule_id": "R-7.4.1", "message": "Four matching pairs required"}]
        required = {"pair:" + str(k) for k in pairs}
    else:
        hs = item.get("hs")
        if not isinstance(hs, dict) or not hs.get("correct_region"):
            return [{"rule_id": "R-7.5", "message": "Correct hotspot region required"}]
        near = hs.get("near_miss_regions")
        if not isinstance(near, list) or len(near) != 2 or len({str(x) for x in near}) != 2:
            return [{"rule_id": "R-7.5", "message": "Two distinct near-miss regions required"}]
        required = {"correct_region", "near_miss:0", "near_miss:1"}
    issues = []
    if set(mapping) != required:
        issues.append({"rule_id": "R-12.4", "message": "Evidence required for each component"})
    for key in required:
        entry = mapping.get(key)
        if not isinstance(entry, dict):
            issues.append({"rule_id": "R-12.4", "message": "Missing component evidence: " + key})
            continue
        refs = entry.get("passage_ids")
        if not isinstance(refs, list) or not refs or any(
            not isinstance(pid, str) or pid not in indexed for pid in refs
        ):
            issues.append({"rule_id": "R-12.4", "message": "Unresolved evidence: " + key})
        explanation = entry.get("explanation")
        if not isinstance(explanation, str) or not explanation.strip():
            issues.append({"rule_id": "R-12.4", "message": "Missing justification: " + key})
    return issues
