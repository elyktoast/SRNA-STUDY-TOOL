"""Safe bridge between extracted lecture files and existing textbook-grounded planning.

Does not save lecture bytes, generate AI questions, or write to the database.
Image-containing slides require visual review before planning.
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
    selected_review = [p["page"] for p in selected
                       if p.get("needs_visual_review", p["page"] in extracted.get("review_pages", []))]
    if not extracted["pages"] and page_start is None and page_end is None:
        selected_review = list(extracted.get("review_pages", []))
    if selected_review:
        return {"jobs": [], "count": 0, "auto_generate": False,
                "auto_publish": False, "database_writes": False,
                "file_extraction": {"filename": filename, "format": extracted["format"],
                                    "page_count": extracted["page_count"], "selected_pages": [p["page"] for p in selected],
                                    "review_pages": selected_review,
                                    "requires_visual_review": True},
                "held_reason": "visual_review_required"}
    text = "\n\n".join("Page "+str(p["page"])+":\n"+p["text"]
                       for p in selected if p["text"])
    if not 1 <= len(text.strip()) <= 12000:
        raise ValueError("Extracted lecture exceeds planning limit; select relevant pages")
    from lecture_to_question_plan import prepare_staging_jobs
    result = prepare_staging_jobs(conn, owner_uid, text, textbook_id=textbook_id,
                                  item_id_factory=item_id_factory, count=count,
                                  mode=mode, format=format, domain=domain,
                                  section=section, objective=objective)
    result["file_extraction"] = {"filename": filename, "format": extracted["format"],
                                 "page_count": extracted["page_count"],
                                 "selected_pages": [p["page"] for p in selected],
                                 "review_pages": [], "requires_visual_review": False}
    return result
