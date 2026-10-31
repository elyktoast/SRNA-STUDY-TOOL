"""Check that each MC/MS answer and distractor has source-linked justification.

This establishes traceability, not clinical truth. A human reviewer must verify
that passages genuinely prove the key and disprove alternatives.
"""
def check(item, trusted_passages):
    if not isinstance(item, dict) or not isinstance(trusted_passages, list):
        raise ValueError("Item and indexed passages required")
    if item.get("format") not in ("MC", "MS"):
        return [{"rule_id": "R-12.4", "message": "Answer evidence for this format not implemented"}]
    indexed = {p["passage_id"]: p for p in trusted_passages
               if isinstance(p, dict) and p.get("passage_id") and p.get("excerpt")}
    options = item.get("options")
    keys = item.get("key")
    mapping = item.get("distractor_evidence")
    if not isinstance(options, list) or not isinstance(keys, list) or not isinstance(mapping, dict):
        return [{"rule_id": "R-12.4", "message": "Missing options, key or option evidence map"}]
    ids = [o.get("id") for o in options if isinstance(o, dict)]
    if len(ids) != len(options) or len(set(ids)) != len(ids) or not keys or any(k not in ids for k in keys):
        return [{"rule_id": "R-12.4", "message": "Invalid option identifiers or key"}]
    issues = []
    if set(mapping) != set(ids):
        issues.append({"rule_id": "R-12.4", "message": "Every keyed and incorrect option needs evidence"})
    for option_id in ids:
        entry = mapping.get(option_id)
        if not isinstance(entry, dict):
            issues.append({"rule_id": "R-12.4", "message": "Missing evidence for option " + str(option_id)})
            continue
        if entry.get("verdict") != ("supports_key" if option_id in keys else "refutes_distractor"):
            issues.append({"rule_id": "R-12.4", "message": "Incorrect evidence verdict for " + str(option_id)})
        refs = entry.get("passage_ids")
        explanation = entry.get("explanation")
        if not isinstance(refs, list) or not refs or any(pid not in indexed for pid in refs):
            issues.append({"rule_id": "R-12.4", "message": "Unresolved option evidence for " + str(option_id)})
        if not isinstance(explanation, str) or not explanation.strip():
            issues.append({"rule_id": "R-12.4", "message": "Missing option justification for " + str(option_id)})
    return issues
