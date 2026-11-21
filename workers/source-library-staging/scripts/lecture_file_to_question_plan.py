"""Safe bridge between extracted lecture files and existing textbook-grounded planning.

Does not save lecture bytes, generate AI questions, or write to the database.
Text-bearing visual slides can plan from extracted text only; image-only slides remain held.
"""
from lecture_file_extraction import extract_lecture

def prepare_lecture_file_jobs(conn, owner_uid, data, filename, *, textbook_id,
                              item_id_factory, count=1, mode="NCE", format="MC",
                              domain=None, section=None, objective=None,
                              enable_ocr=False, page_start=None, page_end=None):
    if type(count) is not int or not 1 <= count <= 5:
        raise ValueError('Question count must be between 1 and 5')
    extracted = extract_lecture(data, filename, enable_ocr=enable_ocr)
    if page_start is not None or page_end is not None:
        if (type(page_start) is not int or type(page_end) is not int
                or not 1 <= page_start <= page_end <= extracted["page_count"]):
            raise ValueError("Invalid lecture page range")
        selected = [p for p in extracted["pages"] if page_start <= p["page"] <= page_end]
    else:
        selected = extracted["pages"]
    if not selected and extracted["pages"]:
        raise ValueError("No lecture pages selected")
    # Report detection, never importance or clinical support inferred from formatting.
    emphasis_pages = {kind: [p["page"] for p in selected
                             if any(isinstance(v, str) and v.strip()
                                    for v in p.get("emphasis", {}).get(kind, []))]
                      for kind in ("highlighted", "bold")}
    # A truly empty page is not a visual concept. Skip it rather than blocking
    # the entire lecture; image-only pages and diagrams remain held for review.
    blank_pages = [p["page"] for p in selected
                   if not p.get("text", "").strip()
                   and not any(p.get(key, 0) for key in ("image_count", "vector_count", "diagram_count"))]
    selected_review = [p["page"] for p in selected
                       if p["page"] not in blank_pages
                       and p.get("needs_visual_review", p["page"] in extracted.get("review_pages", []))]
    if not extracted["pages"] and page_start is None and page_end is None:
        selected_review = list(extracted.get("review_pages", []))
    # Text on a slide is usable without pretending that embedded diagrams were read.
    # Only hold pages whose visual content is the sole available source.
    text_only_visual_pages = [p["page"] for p in selected
                              if p["page"] in selected_review and p.get("text", "").strip()]
    selected_review = [n for n in selected_review if n not in text_only_visual_pages]
    if selected_review:
        return {"jobs": [], "count": 0, "auto_generate": False,
                "auto_publish": False, "database_writes": False,
                "file_extraction": {"filename": filename, "format": extracted["format"],
                                    "page_count": extracted["page_count"], "selected_pages": [p["page"] for p in selected],
                                    "skipped_blank_pages": blank_pages,
                                    "text_only_visual_pages": text_only_visual_pages,
                                    "emphasis_pages": emphasis_pages,
                                    "review_pages": selected_review,
                                    "requires_visual_review": True},
                "held_reason": "visual_review_required"}
    # Chunk by page, then by paragraph for unusually text-heavy pages.
    # Never truncate source text or silently skip an oversized page.
    chunks = []
    current = ""
    for p in selected:
        value = p.get("text", "").strip()
        if not value:
            continue
        prefix = "Page " + str(p["page"]) + ":\n"
        marked = []
        emphasis = p.get("emphasis", {})
        for kind in ("highlighted", "bold"):
            phrases = emphasis.get(kind, [])
            if kind == "highlighted":
                phrases = emphasis.get("planning_highlights", phrases)
            for phrase in phrases:
                phrase = " ".join(phrase.split())
                if 5 <= len(phrase) <= 180 and len(phrase.split()) <= 24:
                    marked.append(f"Lecture {kind}: {phrase}")
        if marked:
            value += "\n\n" + "\n".join(marked)
        remaining = value
        while remaining:
            room = 12000 - len(prefix)
            if room <= 0:
                raise ValueError("Invalid page label")
            if len(remaining) <= room:
                part, remaining = remaining, ""
            else:
                cut = remaining.rfind("\n", 0, room + 1)
                if cut < room // 2:
                    cut = remaining.rfind(" ", 0, room + 1)
                if cut < room // 2:
                    cut = room
                part, remaining = remaining[:cut], remaining[cut:].lstrip()
            entry = prefix + part
            if current and len(current) + 2 + len(entry) > 12000:
                chunks.append(current)
                current = ""
            current = current + ("\n\n" if current else "") + entry
    if current:
        chunks.append(current)
    if not chunks:
        raise ValueError("No extractable lecture text")
    # Bound the work per request without losing content: excess chunks are
    # explicitly reported as pending rather than silently discarded.
    from lecture_to_question_plan import prepare_staging_jobs
    processed = chunks[:5]
    results = [prepare_staging_jobs(conn, owner_uid, chunk, textbook_id=textbook_id,
                                   item_id_factory=item_id_factory, count=count,
                                   mode=mode, format=format, domain=domain,
                                   section=section, objective=objective)
               for chunk in processed]
    result = dict(results[0])
    # Honor the requested count even for a lecture that fits one chunk. Spread
    # slots across processed chunks before taking additional jobs from any one.
    groups = [r.get('jobs', []) for r in results]
    jobs = [group[index] for index in range(count) for group in groups
            if index < len(group)]
    if format == "MC":
        from lecture_concept_extraction import PRIORITY
        priorities = {}
        for chunk in results:
            for topic in chunk.get("lecture_plan", {}).get("topics", []):
                title = topic["title"]
                rank = PRIORITY.get(topic.get("importance"), PRIORITY["standard"])
                priorities[title] = min(priorities.get(title, rank), rank)
        jobs.sort(key=lambda job: priorities.get(job.get("lecture_topic") or job.get("body", {}).get("topic"), PRIORITY["standard"]))
    result["jobs"] = jobs[:count]
    result["count"] = len(result["jobs"])
    result["auto_generate"] = False
    result["auto_publish"] = False
    result["database_writes"] = False
    result["chunk_count"] = len(chunks)
    result["processed_chunk_count"] = len(processed)
    result["remaining_chunk_count"] = len(chunks) - len(processed)
    if len(results) > 1:
        result["classification"] = {"held_count": sum(r.get("classification", {}).get("held_count", 0) for r in results),
                                    "held_for_classification": [item for r in results for item in r.get("classification", {}).get("held_for_classification", [])]}
    # Aggregate diagnostic counts across chunks without exposing lecture text or passages.
    plans = [r.get("lecture_plan", {}) for r in results]
    coverage = [p.get("coverage", {}) for p in plans]
    result["planning_diagnostics"] = {
        "extracted_concepts": sum(c.get("lecture_concepts", 0) for c in coverage),
        "grounded_concepts": sum(c.get("grounded_concepts", 0) for c in coverage),
        "missing_textbook_support": sum(c.get("uncovered_concepts", 0) for c in coverage),
        "classified_jobs": len(result["jobs"]),
        "held_for_classification": result.get("classification", {}).get("held_count", 0),
        "processed_chunks": len(processed),
        "remaining_chunks": len(chunks) - len(processed),
    }
    result["file_extraction"] = {"filename": filename, "format": extracted["format"],
                                 "page_count": extracted["page_count"],
                                 "selected_pages": [p["page"] for p in selected],
                                 "skipped_blank_pages": blank_pages,
                                 "text_only_visual_pages": text_only_visual_pages,
                                 "emphasis_pages": emphasis_pages,
                                 "review_pages": [], "requires_visual_review": False}
    return result
