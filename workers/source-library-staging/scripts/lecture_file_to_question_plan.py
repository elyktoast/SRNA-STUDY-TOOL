"""Safe bridge between extracted lecture files and existing textbook-grounded planning.

Does not save lecture bytes, generate AI questions, or write to the database.
Image-containing slides require visual review before planning.
"""
from lecture_file_extraction import extract_lecture

def prepare_lecture_file_jobs(conn, owner_uid, data, filename, *, textbook_id,
                              item_id_factory, count=1, mode="NCE", format="MC",
                              domain=None, section=None, objective=None,
                              enable_ocr=False):
    extracted = extract_lecture(data, filename, enable_ocr=enable_ocr)
    if extracted["requires_ocr_or_visual_review"]:
        return {"jobs": [], "count": 0, "auto_generate": False,
                "auto_publish": False, "database_writes": False,
                "file_extraction": {"filename": filename, "format": extracted["format"],
                                    "page_count": extracted["page_count"],
                                    "review_pages": extracted["review_pages"],
                                    "requires_visual_review": True},
                "held_reason": "visual_review_required"}
    text = "\n\n".join("Page "+str(p["page"])+":\n"+p["text"]
                       for p in extracted["pages"] if p["text"])
    if not 1 <= len(text.strip()) <= 12000:
        raise ValueError("Extracted lecture exceeds planning limit; select relevant pages")
    from lecture_to_question_plan import prepare_staging_jobs
    result = prepare_staging_jobs(conn, owner_uid, text, textbook_id=textbook_id,
                                  item_id_factory=item_id_factory, count=count,
                                  mode=mode, format=format, domain=domain,
                                  section=section, objective=objective)
    result["file_extraction"] = {"filename": filename, "format": extracted["format"],
                                 "page_count": extracted["page_count"],
                                 "review_pages": [], "requires_visual_review": False}
    return result
