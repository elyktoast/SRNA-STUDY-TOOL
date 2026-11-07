"""Append-only staging revision history; original generated question is never updated.

Caller must use authenticated admin identity, a transaction-capable connection,
and an already source-validated revision proposal. No approval or publication.
"""
import hashlib
import json
from uuid import UUID
from item_draft_storage_v2 import get_draft
from item_draft_revision_v2 import propose_revision


class RevisionValidationError(ValueError):
    def __init__(self, issues):
        self.issues = issues
        super().__init__("Revision still fails source/schema validation")


def digest(item):
    return hashlib.sha256(json.dumps(item,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()


def save_revision(conn, *, owner_uid, draft_id, expected_parent_sha256,
                  citation_excerpts=None, option_evidence=None,
                  reviewer_notes):
    owner, draft_id = (str(UUID(str(x))) for x in (owner_uid,draft_id))
    if not isinstance(expected_parent_sha256,str) or len(expected_parent_sha256)!=64 or any(c not in "0123456789abcdef" for c in expected_parent_sha256):
        raise ValueError("Expected parent digest required")
    if not isinstance(reviewer_notes,str) or not reviewer_notes.strip() or len(reviewer_notes)>5000:
        raise ValueError("Reviewer notes required")
    # Lock the parent row to serialize revision numbers and prevent stale writes.
    with conn.cursor() as cur:
        cur.execute("""select d.id::text from source_library_staging.generated_question_drafts_v2 d
          join source_library_staging.textbooks t on t.id=d.textbook_id
          where d.id=%s::uuid and d.owner_uid=%s::uuid and t.owner_uid=%s::uuid
            and d.status in ('pending_review','needs_revision')
          for update of d""",(draft_id,owner,owner))
        if cur.fetchone() is None:
            raise ValueError("Draft unavailable or finalized")
    parent = get_draft(conn,owner_uid=owner,draft_id=draft_id)
    with conn.cursor() as cur:
        cur.execute("""select revision_number,question_json from source_library_staging.generated_draft_revisions_v2
          where draft_id=%s::uuid and owner_uid=%s::uuid order by revision_number desc limit 1""",
          (draft_id,owner))
        previous=cur.fetchone()
    parent_question = previous[1] if previous else parent["question"]
    if not isinstance(parent_question,dict):
        raise ValueError("Invalid saved revision question")
    if digest(parent_question)!=expected_parent_sha256:
        raise ValueError("Stale revision: parent digest changed")
    refs = parent.get("evidence")
    citations = parent_question.get("evidence")
    if not isinstance(refs,list) or not isinstance(citations,list):
        raise ValueError("Saved citations required")
    ids = {x.get("passage_id") for x in refs+citations if isinstance(x,dict)}
    if not ids or len(ids)>50 or any(not isinstance(x,str) for x in ids):
        raise ValueError("Invalid indexed passage references")
    with conn.cursor() as cur:
        cur.execute("""select p.id::text,p.textbook_id::text,p.page_start,left(p.content,1200)
          from source_library_staging.passages p
          join source_library_staging.textbooks t on t.id=p.textbook_id
          where p.id::text = any(%s::text[]) and t.id=%s::uuid
            and t.owner_uid=%s::uuid and t.status='ready'""",
          (sorted(ids),parent["textbook_id"],owner))
        rows=cur.fetchall()
    trusted_passages=[{"passage_id":r[0],"textbook_id":r[1],
                      "pdf_page_start":r[2],"excerpt":r[3]} for r in rows]
    if len(trusted_passages)!=len(ids):
        raise ValueError("Indexed passage missing from owned textbook")
    proposal=propose_revision({**parent,"question":parent_question},trusted_passages,
        citation_excerpts=citation_excerpts,option_evidence=option_evidence)
    if proposal["issues"]:
        raise RevisionValidationError(proposal["issues"])
    revised=proposal["question"]
    if digest(revised)==expected_parent_sha256:
        raise ValueError("Revision contains no changes")
    revision_number=(previous[0]+1) if previous else 1
    with conn.cursor() as cur:
        cur.execute("""insert into source_library_staging.generated_draft_revisions_v2
          (draft_id,owner_uid,revision_number,parent_question_sha256,revised_question_sha256,
           question_json,issues_json,reviewer_notes)
          values (%s::uuid,%s::uuid,%s,%s,%s,%s::jsonb,%s::jsonb,%s)
          returning id::text""",
          (draft_id,owner,revision_number,expected_parent_sha256,digest(revised),
           json.dumps(revised),json.dumps(proposal["issues"]),reviewer_notes))
        saved=cur.fetchone()
    if not saved:
        raise ValueError("Revision not saved")
    return {"revision_id":saved[0],"draft_id":draft_id,"revision_number":revision_number,
            "question_sha256":digest(revised),"published":False,
            "clinical_review_required":True,"can_publish":False}


def list_revisions(conn, *, owner_uid, draft_id):
    owner,draft_id=(str(UUID(str(x))) for x in (owner_uid,draft_id))
    original=get_draft(conn,owner_uid=owner,draft_id=draft_id)
    with conn.cursor() as cur:
        cur.execute("""select revision_number,id::text,parent_question_sha256,revised_question_sha256,
          reviewer_notes,created_at,question_json from source_library_staging.generated_draft_revisions_v2
          where owner_uid=%s::uuid and draft_id=%s::uuid
          order by revision_number desc limit 100""",(owner,draft_id))
        rows=cur.fetchall()
    current_question=rows[0][6] if rows else original["question"]
    if not isinstance(current_question,dict):
        raise ValueError("Invalid saved revision question")
    return {"draft_id":draft_id,"current_question":current_question,
            "original_question_sha256":digest(original["question"]),
            "current_question_sha256":rows[0][3] if rows else digest(original["question"]),
            "published":False,"revisions":[{"revision_number":r[0],"revision_id":r[1],
             "parent_sha256":r[2],"question_sha256":r[3],
             "notes":r[4],"created_at":r[5].isoformat()} for r in rows]}
