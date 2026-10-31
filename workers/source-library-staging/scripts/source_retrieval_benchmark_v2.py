"""Read-only evaluation of owner-scoped indexed passage retrieval.

Fixtures contain search queries and expected passage IDs/pages, never textbook
excerpts. Does not modify the index or certify clinical/citation accuracy.
"""
def evaluate(search, fixtures, *, min_recall_at_k=0.8):
    if not callable(search):
        raise ValueError("Search callback required")
    if not isinstance(fixtures, list) or not fixtures:
        raise ValueError("Nonempty benchmark fixtures required")
    if not 0 <= min_recall_at_k <= 1:
        raise ValueError("Invalid recall threshold")
    cases = []
    for case in fixtures:
        if not isinstance(case, dict):
            raise ValueError("Invalid benchmark case")
        query = case.get("query")
        expected = case.get("expected_passage_ids")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Search query required")
        if not isinstance(expected, list) or not expected or any(
                not isinstance(p, str) or not p.strip() for p in expected):
            raise ValueError("Expected passage IDs required")
        if len(expected) != len(set(expected)):
            raise ValueError("Duplicate expected passage IDs")
        results = search(query)
        if not isinstance(results, list):
            raise ValueError("Search must return passage records")
        found = [r.get("passage_id") for r in results if isinstance(r, dict)]
        if any(not isinstance(p, str) for p in found):
            raise ValueError("Invalid search result")
        hits = len(set(expected) & set(found))
        cases.append({"query": query, "expected_count": len(expected),
                      "matched_count": hits, "recall_at_k": hits / len(expected),
                      "first_result_relevant": bool(found and found[0] in expected)})
    recall = sum(c["matched_count"] for c in cases) / sum(c["expected_count"] for c in cases)
    return {"passed": recall >= min_recall_at_k,
            "recall_at_k": recall, "threshold": min_recall_at_k,
            "case_count": len(cases), "cases": cases,
            "note": "Retrieval relevance only; original PDF page and clinical claims require separate review"}
