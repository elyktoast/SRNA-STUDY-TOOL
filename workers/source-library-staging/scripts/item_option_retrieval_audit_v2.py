"""Independent, read-only retrieval audit for MC/MS option claims.

Retrieval is not proof of clinical correctness. No model calls or publication.
"""
from search_passages import search, search_many, supports_pipeline
import re


def _measurement_query(label):
    # Retrieval cues only; a nearby verb never establishes clinical truth.
    if not re.fullmatch(r"[A-Za-z -]{3,80}(?:graphy|metry)", label, re.I):
        return None
    return " OR ".join('"' + label + '" ' + verb for verb in ("records", "measures", "detects", "quantifies"))


def _phrase_fallback(label):
    """Search three overlapping label phrases when the complete text has no match."""
    words = re.findall(r"[^\W_]+", label)
    if len(words) < 4:
        return None
    positions = (0, (len(words) - 2) // 2, len(words) - 2)
    pairs = dict.fromkeys(" ".join(words[i:i+2]) for i in positions)
    return " OR ".join('"' + pair + '"' for pair in pairs)


def _definition_rank(row, label):
    text = row.get("excerpt", "").casefold()
    names = list(re.finditer(re.escape(label.casefold()), text))
    verbs = list(re.finditer(r"\b(?:record\w*|measur\w*|detect\w*|quantif\w*)\b", text))
    return max((max(0, 201-abs(v.start()-n.end())) for n in names for v in verbs), default=0)


def audit(conn, owner_uid, item, *, textbook_id, limit=5, context_query=None, textbook_ids=None, matched_passages=None):
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
    if context_query and item["format"] == "MC":
        from build_question_evidence import topic_search_query
        context_query = topic_search_query(context_query)
    from item_source_scope_v2 import source_scope
    books = source_scope(textbook_id, textbook_ids) or [textbook_id]
    searches = {}
    pipeline_enabled = supports_pipeline(conn)

    def prefetch(queries, count):
        missing = list(dict.fromkeys((book, phrase, count) for phrase in queries
                                     for book in books if (book, phrase, count) not in searches))
        for start in range(0, len(missing), 32):
            keys = missing[start:start + 32]
            rows = search_many(conn, owner_uid, [
                (phrase, {"textbook_id": book, "limit": limit})
                for book, phrase, limit in keys])
            searches.update(zip(keys, rows))

    def retrieve(query, count, definition_label=None):
        keys = [(book, query, count) for book in books]
        if pipeline_enabled and len(keys) > 1:
            prefetch([query], count)
        for book, phrase, limit in keys:
            if (book, phrase, limit) not in searches:
                searches[book, phrase, limit] = search(conn, phrase, owner_uid, limit=limit, textbook_id=book)
        groups = [list(searches[key]) for key in keys]
        if definition_label:
            for group in groups:
                group.sort(key=lambda row: -_definition_rank(row, definition_label))
            groups.sort(key=lambda group: -_definition_rank(group[0], definition_label) if group else 0)
        return [group[index] for index in range(count) for group in groups if index < len(group)][:count]
    context_rows = []
    context_failed = False
    if context_query:
        try:
            context_rows = retrieve(context_query.strip(), min(limit, 2))
        except Exception:
            context_failed = True
    planned = []
    for option in options:
        label = option.get("text")
        if not isinstance(label, str) or not label.strip():
            raise ValueError("Every option needs text")
        query = label[:180].strip()
        definition = _measurement_query(query) if item["format"] == "MC" else None
        planned.append((option["id"], query, definition))
    budget = max(1, limit - len(context_rows))
    prefetch_failed = False
    if pipeline_enabled and not context_failed:
        try:
            prefetch([phrase for _, query, definition in planned
                       for phrase in (definition, query) if phrase], budget)
        except Exception:
            # A failed pipeline can invalidate later replies in that group.
            # Leave every affected option pending independent verification.
            prefetch_failed = True
    results = []
    search_failed = context_failed or prefetch_failed
    missing_evidence = False
    for option_id, query, definition_query in planned:
        queries = ([definition_query] if definition_query else []) + [query] + ([context_query.strip()] if context_query else [])
        try:
            if prefetch_failed:
                raise ValueError("Independent passage search unavailable")
            definitions = retrieve(definition_query, budget, query) if definition_query else []
            ordinary = retrieve(query, budget)
            option_rows = list({row["passage_id"]: row for row in definitions + ordinary}.values())[:budget]
            if not option_rows and not context_rows and item["format"] == "MC":
                fallback = _phrase_fallback(query)
                if fallback:
                    queries.append(fallback)
                    option_rows = retrieve(fallback, budget)
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
        if matched_passages is not None and search_status == "matches_found":
            matched_passages.update((row["passage_id"], row) for row in rows)
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
