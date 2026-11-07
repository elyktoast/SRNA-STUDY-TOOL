"""Read-only, no-model validation of an owned unpublished staging draft.

Uses the saved question and the *current* indexed passage text. No mutation,
approval, publication, paid model call, or inferred clinical verification.
"""
from item_draft_storage_v2 import get_draft
from item_generation_contract_v2 import validate_complete_item
from item_source_reconciliation_v2 import reconcile
from item_answer_evidence_v2 import check as check_answers
from item_special_format_evidence_v2 import check as check_special


def revalidate(conn, *, owner_uid, draft_id):
    draft = get_draft(conn, owner_uid=owner_uid, draft_id=draft_id)
    if draft["published"] is not False:
        raise ValueError("Published question cannot be revalidated here")
    item = draft["question"]
    if not isinstance(item, dict):
        raise ValueError("Invalid saved question")
    # Restrict retrieval to cited and saved evidence IDs, same owned textbook.
    refs = draft["evidence"]
    ids = {e.get("passage_id") for e in refs if isinstance(e, dict)}
    ids.update(e.get("passage_id") for e in item.get("evidence", []) if isinstance(e, dict))
    if not ids or len(ids) > 50 or any(not isinstance(x, str) for x in ids):
        raise ValueError("Invalid saved evidence references")
    with conn.cursor() as cur:
        cur.execute("""
          select p.id::text,p.textbook_id::text,p.page_start,left(p.content,1200)
          from source_library_staging.passages p
          join source_library_staging.textbooks t on t.id=p.textbook_id
          where p.id::text = any(%s::text[]) and t.id=%s::uuid
            and t.owner_uid=%s::uuid and t.status='ready'
        """, (sorted(ids), draft["textbook_id"], owner_uid))
        rows = cur.fetchall()
    passages = [{"passage_id":r[0],"textbook_id":r[1],
                 "pdf_page_start":r[2],"excerpt":r[3]} for r in rows]
    found = {p["passage_id"] for p in passages}
    issues = validate_complete_item(item)
    for pid in sorted(ids-found):
        issues.append({"rule_id":"R-2.5","message":"Saved passage is missing from current index: "+pid})
    if passages:
        issues.extend(reconcile(item, passages))
        issues.extend(check_answers(item, passages) if item.get("format") in ("MC","MS")
                      else check_special(item, passages))
    else:
        issues.append({"rule_id":"R-2.5","message":"No indexed passages available"})
    return {"draft_id":draft_id,"status":draft["status"],"published":False,
            "validation":"read_only_current_index","can_publish":False,
            "clinical_review_required":True,"issues":issues,
            "indexed_passages_found":len(passages),"indexed_passages_requested":len(ids),
            "generation_performed":False,"database_writes":False}
