"""Independent, read-only retrieval audit for MC/MS option claims.

Retrieval is not proof of clinical correctness. No model calls or publication.
"""
from search_passages import search


def audit(conn, owner_uid, item, *, textbook_id, limit=5, context_query=None):
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
    if context_query is not None and (not isinstance(context_query, str) or not context_query.strip() or len(context_query) > 500):
        raise ValueError("Invalid independent retrieval context")
    if context_query and limit < 2:
        raise ValueError("Context-aware retrieval requires at least two candidates")
    context_rows = []
    context_failed = False
    if context_query:
        try:
            context_rows = search(conn, context_query.strip(), owner_uid, limit=limit, textbook_id=textbook_id)
        except Exception:
            context_failed = True
    results = []
    search_failed = context_failed
    missing_evidence = False
    for option in options:
        option_id = option["id"]
        label = option.get("text")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Every option needs text")
        query = label[:180].strip()
        queries = [query] + ([context_query.strip()] if context_query else [])
        try:
            option_rows = search(conn, query, owner_uid, limit=limit - 1 if context_query else limit, textbook_id=textbook_id)
        except Exception:
            option_rows = []
            search_failed = True
            option_failed = True
        else:
            option_failed = False
        # A topic table and an option's classification can be on different pages.
        # Keep independently searched option matches first, then fill the bounded
        # per-option budget with context. Paired concepts may span two pages;
        # an unmatched option must not lose the second half of that evidence.
        rows = list({row["passage_id"]: row for row in option_rows + context_rows}.values())[:limit]
        search_status = "failed" if option_failed or context_failed else "matches_found" if rows else "no_matches"
        if not rows:
            missing_evidence = True
        results.append({
            "option_id": option_id,
            "question_context": stem[:180],
            "search_query": query,
            "search_queries": queries,
            "expected_verdict": "supports_key" if option_id in keys else "refutes_distractor",
            "retrieved_passage_ids": [row["passage_id"] for row in rows],
            "retrieved_count": len(rows),
            "search_status": search_status,
            "independent_verification": "pending",
            "contradiction_checked": False,
        })
    return {
        "option_audits": results,
        "all_options_searched": not search_failed,
        "all_options_have_matches": not search_failed and not missing_evidence,
        "clinical_verification_complete": False,
        "can_publish": False,
        "requires_human_review": True,
    }
