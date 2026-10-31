"""Strict excerpt traceability for v2.0 drafts; does not prove clinical truth.

Passages are trusted backend data supplied by caller, never inferred from citations.
"""
def check(item, passages):
    issues = []
    if not isinstance(passages, dict):
        return [{"rule_id": "R-2.5", "message": "Trusted passage index required"}]
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return [{"rule_id": "R-2.5", "message": "Evidence missing"}]
    for entry in evidence:
        if not isinstance(entry, dict):
            issues.append({"rule_id": "R-2.5", "message": "Malformed evidence entry"})
            continue
        passage_id = entry.get("passage_id")
        source = passages.get(passage_id)
        if not isinstance(source, dict):
            issues.append({"rule_id": "R-2.5", "message": "Passage ID unresolved"})
            continue
        for field in ("textbook_id", "pdf_page"):
            if str(entry.get(field)) != str(source.get(field)):
                issues.append({"rule_id": "R-2.5", "message": field + " does not match indexed passage"})
        excerpt = entry.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in source.get("text", ""):
            issues.append({"rule_id": "R-2.5", "message": "Evidence excerpt not found verbatim in passage"})
    return issues
