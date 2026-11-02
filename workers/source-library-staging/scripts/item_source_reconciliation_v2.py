"""Reconcile generated citations against trusted indexed passages.

Never treats an AI citation or model's verification claim as authoritative.
PDF page locations are not verified printed-page references.
"""
def reconcile(item, trusted_passages):
    if not isinstance(item, dict) or not isinstance(trusted_passages, list):
        raise ValueError("Item and trusted passages required")
    indexed = {}
    for passage in trusted_passages:
        if not isinstance(passage, dict) or not all(
            passage.get(k) for k in ("passage_id", "textbook_id", "excerpt")
        ):
            raise ValueError("Invalid trusted passage")
        if passage["passage_id"] in indexed:
            raise ValueError("Duplicate trusted passage ID")
        indexed[passage["passage_id"]] = passage
    evidence = item.get("evidence")
    if not isinstance(evidence, list) or not evidence:
        return [{"rule_id": "R-12.4", "message": "Missing item evidence"}]
    issues = []
    for index, citation in enumerate(evidence):
        if not isinstance(citation, dict):
            issues.append({"rule_id": "R-12.4", "message": "Invalid evidence entry"})
            continue
        pid = citation.get("passage_id")
        source = indexed.get(pid)
        if source is None:
            issues.append({"rule_id": "R-12.4", "message": "Unknown passage ID at index " + str(index)})
            continue
        if citation.get("textbook_id") != source["textbook_id"]:
            issues.append({"rule_id": "R-12.4", "message": "Textbook mismatch at index " + str(index)})
        excerpt = citation.get("excerpt")
        if not isinstance(excerpt, str) or not excerpt.strip() or excerpt not in source["excerpt"]:
            issues.append({"rule_id": "R-12.4", "message": "Excerpt mismatch at index " + str(index)})
        actual_page = source.get("pdf_page_start")
        if actual_page is not None and citation.get("pdf_page") != actual_page:
            issues.append({"rule_id": "R-12.4", "message": "PDF page mismatch at index " + str(index)})
        if citation.get("printed_page_verified") is True:
            issues.append({"rule_id": "R-17", "message": "Printed page requires independent human verification"})
    return issues
