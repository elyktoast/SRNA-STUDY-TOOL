"""Read-only intake of NEW v2.0 drafts from trusted backend generator.

Never migrate legacy question bank, write DB, call AI, or auto-approve.
Reject mixed legacy/v2 drafts rather than silently converting schemas.
"""
from item_screening_orchestrator import screen


def intake(generated, *, passages=None, known_stems=(), source_texts=(),
           calculations=None, embeddings=None, neighbors=None):
    if not isinstance(generated, dict) or not isinstance(generated.get("questions"), list):
        raise ValueError("Expected v2.0 generator response with questions list")
    drafts = generated["questions"]
    if not 1 <= len(drafts) <= 20:
        raise ValueError("Draft count must be between 1 and 20")
    ids = [item.get("item_id") if isinstance(item, dict) else None for item in drafts]
    if any(not isinstance(i, str) or not i.strip() for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("New drafts require unique nonempty IDs")
    if any(item.get("rules_version") != "2.0" for item in drafts):
        raise ValueError("Legacy generator output is not a v2.0 item; explicit adapter required")
    results = []
    stems = list(known_stems)
    for item in drafts:
        item_id = item["item_id"]
        result = screen(
            item, known_stems=stems, source_texts=source_texts, passages=passages,
            calculation=(calculations or {}).get(item_id),
            embedding=(embeddings or {}).get(item_id),
            neighbors=neighbors,
        )
        results.append({"item_id": item_id, "status": result["next_state"],
                        "screening": result, "requires_human_review": True})
        if isinstance(item.get("stem"), str):
            stems.append(item["stem"])
    return {"count": len(results), "draft_reviews": results,
            "auto_approved": False, "database_writes": False}
