"""Trusted staging handoff from generated draft to read-only screening.

Never publishes or persists drafts. Missing verification inputs remain pending.
"""
from item_generation_runner_v2 import generate_one
from item_draft_intake import intake

def generate_and_screen(adapter, *, mode, domain, section, objective, evidence,
                        format="MC", item_id, known_stems=(), calculation=None,
                        embedding=None, neighbors=None):
    generated = generate_one(adapter, mode=mode, domain=domain,
                             section=section, objective=objective,
                             evidence=evidence, format=format, item_id=item_id)
    if generated["schema_issues"]:
        return {"item_id": item_id, "item": generated["item"],
                "generator_issues": generated["schema_issues"],
                "screening": None, "next_state": "needs_source_review"
                if any(x["rule_id"] in ("R-12.4", "R-17") for x in generated["schema_issues"])
                else "needs_editorial_review",
                "requires_human_review": True, "can_publish": False,
                "database_writes": False}
    indexed = {p["passage_id"]: {
        "passage_id": p["passage_id"], "textbook_id": p["textbook_id"],
        "pdf_page_start": p.get("pdf_page_start"), "text": p["excerpt"]}
        for p in evidence}
    review = intake({"questions": [generated["item"]]},
                    passages=indexed, known_stems=known_stems,
                    source_texts=[p["excerpt"] for p in evidence],
                    calculations={item_id: calculation} if calculation is not None else None,
                    embeddings={item_id: embedding} if embedding is not None else None,
                    neighbors=neighbors)
    result = review["draft_reviews"][0]
    return {"item_id": item_id, "item": generated["item"],
            "generator_issues": [], "screening": result["screening"],
            "next_state": result["status"], "requires_human_review": True,
            "can_publish": False, "database_writes": False}
