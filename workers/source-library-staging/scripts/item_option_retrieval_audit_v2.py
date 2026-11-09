"""Independent, read-only retrieval audit for MC/MS option claims.

Retrieval is not proof of clinical correctness. No model calls or publication.
"""
from search_passages import search


def audit(conn, owner_uid, item, *, textbook_id, limit=5):
    if not isinstance(item, dict) or item.get("format") not in ("MC", "MS"):
        raise ValueError("MC/MS item required")
    if not isinstance(textbook_id, str) or not textbook_id:
        raise ValueError("Explicit indexed textbook required")
    if type(limit) is not int or not 1 <= limit <= 10:
        raise ValueError("Per-option retrieval limit must be 1..10")
    stem = item.get("stem")
    options = item.get("options")
    keys = item.get("key")
    if not isinstance(stem, str) or not stem.strip() or not isinstance(options, list) or not options or not isinstance(keys, list):
        raise ValueError("Complete item stem, options, and key required")
    ids = [option.get("id") for option in options if isinstance(option, dict)]
    if len(ids) != len(options) or len(set(ids)) != len(ids) or not keys or any(k not in ids for k in keys):
        raise ValueError("Valid option identifiers and key required")
    results = []
    incomplete = False
    for option in options:
        option_id = option["id"]
        # Do not treat source silence as evidence that a distractor is false.
        label = option.get("text")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Every option needs text")
        query = label[:180].strip()
        try:
            rows = search(conn, query, owner_uid, limit=limit, textbook_id=textbook_id)
        except Exception:
            rows = []
            incomplete = True
            search_status = "failed"
        else:
            search_status = "matches_found" if rows else "no_matches"
            if not rows:
                incomplete = True
        results.append({
            "option_id": option_id,
            "question_context": stem[:180],
            "search_query": query,
            "expected_verdict": "supports_key" if option_id in keys else "refutes_distractor",
            "retrieved_passage_ids": [row["passage_id"] for row in rows],
            "retrieved_count": len(rows),
            "search_status": search_status,
            "independent_verification": "pending",
            "contradiction_checked": False,
        })
    return {
        "option_audits": results,
        "all_options_searched": not incomplete,
        "clinical_verification_complete": False,
        "can_publish": False,
        "requires_human_review": True,
    }
