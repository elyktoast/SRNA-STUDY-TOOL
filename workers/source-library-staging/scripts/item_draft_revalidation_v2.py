"""Read-only, no-model validation of an owned unpublished staging draft.

Uses the saved question and the *current* indexed passage text. No mutation,
approval, publication, paid model call, or inferred clinical verification.
"""
from item_draft_storage_v2 import get_draft
from item_generation_contract_v2 import validate_complete_item
from item_source_reconciliation_v2 import reconcile
from item_answer_evidence_v2 import check as check_answers
from item_special_format_evidence_v2 import check as check_special
from item_generation_runner_v2 import _complete_nonclinical_schema_fields
from item_source_reconciliation_v2 import _format_normalized

MAX_VERIFICATION_PASSAGE_CHARS = 200_000


def revalidate(conn, *, owner_uid, draft_id):
    draft = get_draft(conn, owner_uid=owner_uid, draft_id=draft_id)
    if draft["published"] is not False or draft["status"] not in ("pending_review", "needs_revision"):
        raise ValueError("Only unpublished drafts awaiting review can be revalidated")
    item = draft["question"]
    if not isinstance(item, dict):
        raise ValueError("Invalid saved question")
    # Restrict retrieval to cited and saved evidence IDs, same owned textbook.
    refs = draft["evidence"]
    citations = item.get("evidence", [])
    if not isinstance(refs, list) or not isinstance(citations, list):
        raise ValueError("Invalid saved evidence references")
    ids = {e.get("passage_id") for e in refs if isinstance(e, dict)}
    ids.update(e.get("passage_id") for e in citations if isinstance(e, dict))
    if not ids or len(ids) > 50 or any(not isinstance(x, str) for x in ids):
        raise ValueError("Invalid saved evidence references")
    with conn.cursor() as cur:
        cur.execute("""
          select p.id::text,p.textbook_id::text,p.page_start,p.content
          from source_library_staging.passages p
          join source_library_staging.textbooks t on t.id=p.textbook_id
          where p.id::text = any(%s::text[]) and t.id=%s::uuid
            and t.owner_uid=%s::uuid and t.status='ready'
        """, (sorted(ids), draft["textbook_id"], owner_uid))
        rows = cur.fetchall()
    # Never treat a truncated passage as proof that a valid quotation is absent.
    # Fail closed on unusually large indexed passages rather than silently clipping them.
    if any(not isinstance(r[3], str) or len(r[3]) > MAX_VERIFICATION_PASSAGE_CHARS for r in rows):
        raise ValueError("Indexed passage exceeds safe citation verification limit")
    passages = [{"passage_id":r[0],"textbook_id":r[1],
                 "pdf_page_start":r[2],"excerpt":r[3]} for r in rows]
    found = {p["passage_id"] for p in passages}
    # Apply only safe, deterministic legacy schema defaults in memory. Never
    # mutate the stored draft or invent clinical/source assertions.
    normalized = _complete_nonclinical_schema_fields(item)
    normalized_fields = [k for k in ("sa", "dd", "hs", "audit", "self_check", "stats")
                         if k not in item and k in normalized]
    issues = validate_complete_item(normalized)
    if not citations:
        issues.append({"rule_id":"R-2.5","message":"Saved question has no citations"})
    for pid in sorted(ids-found):
        issues.append({"rule_id":"R-2.5","message":"Saved passage is missing from current index: "+pid})
    if passages and citations:
        issues.extend(reconcile(normalized, passages))
    if passages:
        issues.extend(check_answers(normalized, passages) if normalized.get("format") in ("MC","MS")
                      else check_special(normalized, passages))
    else:
        issues.append({"rule_id":"R-2.5","message":"No indexed passages available"})
    # Supply a reviewable citation repair candidate only for an absent quote.
    # A nonempty mismatched quotation is NOT silently replaced: it could
    # indicate a materially different source or clinical assertion.
    source_by_id = {p["passage_id"]:p for p in passages}
    citation_repair_candidates = []
    for index, citation in enumerate(citations):
        if not isinstance(citation, dict):
            continue
        source = source_by_id.get(citation.get("passage_id"))
        if source is None or citation.get("textbook_id") != source["textbook_id"]:
            continue
        quote = citation.get("excerpt")
        absent = not isinstance(quote, str) or not quote.strip()
        mismatch = absent or _format_normalized(quote) not in _format_normalized(source["excerpt"])
        if mismatch:
            citation_repair_candidates.append({
                "citation_index":index, "passage_id":source["passage_id"],
                "reason":"missing_excerpt" if absent else "mismatched_excerpt",
                "suggested_excerpt":source["excerpt"] if absent else None,
                "indexed_excerpt_preview":source["excerpt"][:500],
                "requires_human_source_verification":True,
                "automatically_applied":False})
    options = normalized.get("options") if isinstance(normalized.get("options"), list) else []
    mapping = normalized.get("distractor_evidence")
    mapping = mapping if isinstance(mapping, dict) else {}
    keys = normalized.get("key") if isinstance(normalized.get("key"), list) else []
    evidence_worksheet = [
        {"option_id":o["id"], "option_text":o.get("text"),
         "expected_verdict":"supports_key" if o["id"] in keys else "refutes_distractor",
         "current_evidence":mapping.get(o["id"]), "human_verification_required":True}
        for o in options if isinstance(o, dict) and isinstance(o.get("id"), str)
    ]
    return {"draft_id":draft_id,"status":draft["status"],"published":False,
            "validation":"read_only_current_index","can_publish":False,
            "clinical_review_required":True,"issues":issues,
            "indexed_passages_found":len(passages),"indexed_passages_requested":len(ids),
            "generation_performed":False,"database_writes":False,
            "legacy_defaults_applied_in_memory":normalized_fields,
            "source_excerpt_review": [{"passage_id":p["passage_id"],"pdf_page":p["pdf_page_start"],
                "indexed_excerpt_preview":p["excerpt"][:500]} for p in passages],
            "saved_question_modified":False,
            "option_evidence_worksheet":evidence_worksheet,
            "citation_repair_candidates":citation_repair_candidates,
            "normalized_question_preview":normalized}
