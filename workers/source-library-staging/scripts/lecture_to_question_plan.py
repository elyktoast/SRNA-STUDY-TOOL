"""Private lecture-text planning pipeline backed by indexed textbook retrieval.

Read-only. Never sends lecture or textbook material to public services.
"""
from lecture_concept_extraction import PRIORITY, extract
from lecture_question_plan import plan
from build_question_evidence import (_source_records, build_evidence, lecture_focus_queries,
                                     topic_search_query)
from search_passages import search, search_many, supports_pipeline


def valid_staging_count(count, format):
    return type(count) is int and (1 <= count <= 5 or (format == "MC" and count in (25, 50, 100)))


def prepare(conn, owner_uid, lecture_text, *, textbook_id=None, count=20,
            max_concepts=30, passage_limit=6, prefer_learning_objectives=False):
    extracted = extract(lecture_text, max_concepts=max_concepts)
    concepts = extracted["concepts"]
    if prefer_learning_objectives:
        concepts = sorted(concepts, key=lambda topic: PRIORITY[topic["importance"]])
    evidence = {}
    for topic in concepts:
        result = build_evidence(conn, owner_uid, topic["title"],
                                textbook_id=textbook_id, limit=passage_limit,
                                **({'balance_books':True} if textbook_id is None else {}))
        evidence[topic["title"]] = result["sources"]
    planned = plan(concepts, evidence, count=count) if concepts else {
        "requested": count, "planned": 0, "topics": [],
        "missing_textbook_support": [], "coverage": {
            "lecture_concepts": 0, "grounded_concepts": 0, "uncovered_concepts": 0},
        "auto_approved": False, "database_writes": False,
    }
    return {**planned, "extraction": {
        "method": extracted["extraction_method"],
        "requires_review": True,
        "candidate_count": len(concepts),
        "no_candidates_found": not bool(concepts),
    }, "lecture_text_stored": False}


def _prepare_grounded_mc_batch(conn, owner_uid, lecture_text, *, textbook_id, count):
    """Prepare one job per independently retrieved lecture focus before repeats."""
    extracted = extract(lecture_text, max_concepts=30)
    concepts = sorted(extracted["concepts"], key=lambda topic: PRIORITY[topic["importance"]])
    if not concepts:
        return {"requested": count, "planned": 0, "topics": [], "missing_textbook_support": [],
                "coverage": {"lecture_concepts": 0, "grounded_concepts": 0, "uncovered_concepts": 0},
                "extraction": {"method": extracted["extraction_method"], "requires_review": True,
                               "candidate_count": 0, "no_candidates_found": True},
                "focus_preflight": {"checked": 0, "grounded": 0, "held": 0}}

    candidates = {}
    for concept in concepts:
        title = concept["title"]
        points = concept.get("learning_points") or []
        candidates[title] = [
            (title + " — " + point, lecture_focus_queries(title, point)) for point in points
        ] if points else [(title, [topic_search_query(title)])]
    candidate_rows = [queries for variants in candidates.values() for _, queries in variants]
    scope = {"textbook_id": textbook_id, "limit": 6}
    hits = {}
    pipeline = supports_pipeline(conn)
    # Only search the next, shorter candidate for learning points that
    # still have no match. Deduplicate queries across headings and slides.
    def matched(queries):
        return next((hits[query] for query in queries if hits.get(query)), [])

    for index in range(max((len(queries) for queries in candidate_rows), default=0)):
        queries = list(dict.fromkeys(options[index] for options in candidate_rows
                        if index < len(options) and options[index] not in hits and not matched(options)))
        if pipeline:
            for offset in range(0, len(queries), 32):
                chunk = queries[offset:offset + 32]
                results = search_many(conn, owner_uid, [(query, scope) for query in chunk])
                hits.update((query, _source_records(rows)) for query, rows in zip(chunk, results, strict=True))
        else:
            for query in queries:
                hits[query] = _source_records(search(conn, query, owner_uid, **scope))

    variants_by_title = {}
    seen = set()
    for title, candidates_for_title in candidates.items():
        variants = []
        for topic, queries in candidates_for_title:
            key = " ".join(topic.casefold().split())
            evidence = matched(queries)
            if evidence and key not in seen:
                seen.add(key)
                variants.append({"topic": topic, "evidence": evidence})
        variants_by_title[title] = variants
    planned = plan(concepts, {title: variants[0]["evidence"] for title, variants in
                              variants_by_title.items() if variants}, count=count)
    # Allocate across headings before using a second focus from the same
    # heading. Leave any repeat attempts to the accepted-target queue.
    available = [(topic, variants) for topic in planned["topics"]
                 if (variants := variants_by_title[topic["title"]])]
    for topic, _ in available:
        topic["verified_variants"] = []
    remaining = count
    for index in range(max((len(variants) for _, variants in available), default=0)):
        for topic, variants in available:
            if index < len(variants) and remaining:
                topic["verified_variants"].append(variants[index])
                remaining -= 1
        if not remaining:
            break
    for topic, _ in available:
        topic["question_count"] = len(topic["verified_variants"])
    planned["planned"] = count - remaining
    checked = sum(len(variants) for variants in candidates.values())
    grounded = sum(bool(matched(queries)) for queries in candidate_rows)
    planned["focus_preflight"] = {"checked": checked, "grounded": grounded, "held": checked - grounded}
    planned["extraction"] = {"method": extracted["extraction_method"], "requires_review": True,
                             "candidate_count": len(concepts), "no_candidates_found": False}
    return planned


def prepare_staging_jobs(conn, owner_uid, lecture_text, *, textbook_id,
                         item_id_factory, mode="NCE", format="MC", count=1,
                         domain=None, section=None, objective=None):
    """Compose extraction, indexed retrieval, blueprint selection and v2 handoff.

    Produces preflight requests only. No network calls, paid AI generation,
    draft persistence, or publication. The trusted authenticated service must
    execute any generated jobs separately after explicit owner authorization.
    """
    if textbook_id is not None and (not isinstance(textbook_id, str) or not textbook_id.strip()):
        raise ValueError("Invalid textbook selection")
    if not valid_staging_count(count, format):
        raise ValueError("Unsupported staging question count")
    from lecture_generation_requests import requests, staging_http_jobs
    if format == "MC" and count >= 25:
        planned = _prepare_grounded_mc_batch(conn, owner_uid, lecture_text, textbook_id=textbook_id, count=count)
    else:
        planned = prepare(conn, owner_uid, lecture_text, textbook_id=textbook_id,
                          count=count, prefer_learning_objectives=format == "MC")
    selected = requests(planned, mode=mode, domain=domain,
                        section=section, objective=objective, format=format)
    handoff = staging_http_jobs(selected, textbook_id=textbook_id,
                                item_id_factory=item_id_factory, execute=False)
    # Return derived question topics/focus only, never textbook excerpts or the
    # full lecture text. Unselected bullet collections stay internal.
    public_plan = {
        "requested": planned["requested"],
        "planned": planned["planned"],
        "coverage": planned["coverage"],
        "extraction": planned["extraction"],
        **({"focus_preflight": planned["focus_preflight"]} if "focus_preflight" in planned else {}),
        "lecture_text_stored": False,
        "topics": [
            {"title": topic["title"],
             "question_count": topic["question_count"],
             "importance": topic.get("importance", "standard"),
             "lecture_locator": topic.get("lecture_locator")}
            for topic in planned["topics"]
        ],
        "missing_textbook_support": [{k:v for k,v in t.items() if k != "learning_points"}
                                     for t in planned["missing_textbook_support"]],
    }
    return {"lecture_plan": public_plan, "classification": {
                "held_for_classification": selected["held_for_classification"],
                "held_count": selected["held_count"]},
            **handoff, "auto_generate": False, "auto_publish": False,
            "database_writes": False}
