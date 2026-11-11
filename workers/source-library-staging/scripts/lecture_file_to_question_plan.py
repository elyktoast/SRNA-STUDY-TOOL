"""Safe bridge between extracted lecture files and existing textbook-grounded planning.

Does not save lecture bytes, generate AI questions, or write to the database.
Text-bearing visual slides can plan from extracted text only; image-only slides remain held.
"""
from lecture_file_extraction import extract_lecture

def prepare_lecture_file_jobs(conn, owner_uid, data, filename, *, textbook_id,
                              item_id_factory, count=1, mode="NCE", format="MC",
                              domain=None, section=None, objective=None,
                              enable_ocr=False, page_start=None, page_end=None):
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
                                   item_id_factory=item_id_factory, count=1,
                                   mode=mode, format=format, domain=domain,
                                   section=section, objective=objective)
               for chunk in processed]
    result = dict(results[0])
    result["jobs"] = [job for r in results for job in r.get("jobs", [])][:count]
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
    result["file_extraction"] = {"filename": filename, "format": extracted["format"],
                                 "page_count": extracted["page_count"],
                                 "selected_pages": [p["page"] for p in selected],
                                 "skipped_blank_pages": blank_pages,
                                 "text_only_visual_pages": text_only_visual_pages,
                                 "review_pages": [], "requires_visual_review": False}
    return result
