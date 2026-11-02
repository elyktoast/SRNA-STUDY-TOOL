"""Private staging-only draft storage. Call only from an authenticated admin service.

No public HTTP route and no canonical question-bank publication.
The caller owns the transaction and must verify reviewer identity.
"""
import json
from uuid import UUID
from item_draft_review_contract_v2 import validate_draft, validate_review

def save(conn, payload):
    outcome = validate_draft(payload)
    owner = str(UUID(str(payload["owner_uid"])))
    book = str(UUID(str(payload["textbook_id"])))
    metadata = ("topic", "domain", "section", "objective", "provider", "model")
    if any(not isinstance(payload.get(k), str) or not payload[k].strip()
           or len(payload[k]) > 500 for k in metadata):
        raise ValueError("Missing draft metadata")
    with conn.cursor() as cur:
        cur.execute("""
          insert into source_library_staging.generated_question_drafts_v2
          (owner_uid,textbook_id,topic,exam_mode,question_format,
           blueprint_domain,blueprint_section,blueprint_objective,
           provider,model,question_json,screening_json,evidence_json)
          select t.owner_uid,t.id,%s,%s,%s,%s,%s,%s,%s,%s,
                 %s::jsonb,%s::jsonb,%s::jsonb
          from source_library_staging.textbooks t
          where t.id=%s::uuid and t.owner_uid=%s::uuid and t.status='ready'
            and not exists (
              select 1 from jsonb_array_elements(%s::jsonb) ev
              where not exists (
                select 1 from source_library_staging.passages p
                where p.id::text = ev->>'passage_id'
                  and p.textbook_id = t.id
              )
            )
          returning id::text
        """, (payload["topic"],payload["mode"],payload["format"],
              payload["domain"],payload["section"],payload["objective"],
              payload["provider"],payload["model"],
              json.dumps(payload["question"]),json.dumps(payload["screening"]),
              json.dumps(payload["evidence"]),book,owner,json.dumps(payload["evidence"])))
        record = cur.fetchone()
    if not record:
        raise ValueError("Textbook not ready, not owned by admin, or evidence not indexed in this textbook")
    return {"draft_id": record[0], **outcome}

def review(conn, *, owner_uid, reviewer_uid, draft_id, status, notes):
    outcome = validate_review(status, reviewer_uid, notes)
    owner, reviewer, draft = (str(UUID(str(x))) for x in
                              (owner_uid, reviewer_uid, draft_id))
    with conn.cursor() as cur:
        cur.execute("""
          update source_library_staging.generated_question_drafts_v2 d
          set status=%s,reviewer_notes=%s,reviewed_by=%s::uuid,
              reviewed_at=now(),updated_at=now()
          from source_library_staging.textbooks t
          where d.id=%s::uuid and d.owner_uid=%s::uuid
            and d.textbook_id=t.id and t.owner_uid=%s::uuid
            and d.status in ('pending_review','needs_revision')
          returning d.id::text
        """, (status,notes,reviewer,draft,owner,owner))
        record = cur.fetchone()
    if not record:
        raise ValueError("Draft not found or already finalized")
    return {"draft_id": record[0], **outcome}

def list_drafts(conn, *, owner_uid, limit=50):
    owner = str(UUID(str(owner_uid)))
    if type(limit) is not int or not 1 <= limit <= 100:
        raise ValueError("Invalid limit")
    with conn.cursor() as cur:
        cur.execute("""
          select d.id::text,d.topic,d.exam_mode,d.question_format,
                 d.status,d.created_at,d.textbook_id::text
          from source_library_staging.generated_question_drafts_v2 d
          join source_library_staging.textbooks t on t.id=d.textbook_id
          where d.owner_uid=%s::uuid and t.owner_uid=%s::uuid
          order by d.created_at desc,d.id desc limit %s
        """, (owner,owner,limit))
        rows = cur.fetchall()
    return [{"draft_id":x[0],"topic":x[1],"mode":x[2],
             "format":x[3],"status":x[4],"created_at":x[5].isoformat(),
             "textbook_id":x[6]} for x in rows]


def get_draft(conn, *, owner_uid, draft_id):
    """Retrieve a complete private draft for the authenticated owner.

    The HTTP caller must resolve owner_uid from a verified admin session,
    never from a client-supplied request body.
    """
    owner = str(UUID(str(owner_uid)))
    draft = str(UUID(str(draft_id)))
    with conn.cursor() as cur:
        cur.execute("""
          select d.id::text,d.textbook_id::text,d.topic,d.exam_mode,
                 d.question_format,d.blueprint_domain,d.blueprint_section,
                 d.blueprint_objective,d.provider,d.model,d.question_json,
                 d.screening_json,d.evidence_json,d.status,d.reviewer_notes,
                 d.reviewed_by::text,d.reviewed_at,d.created_at,d.updated_at
          from source_library_staging.generated_question_drafts_v2 d
          join source_library_staging.textbooks t on t.id=d.textbook_id
          where d.id=%s::uuid and d.owner_uid=%s::uuid
            and t.owner_uid=%s::uuid
        """, (draft, owner, owner))
        row = cur.fetchone()
    if row is None:
        raise ValueError("Draft not found")
    keys = ("draft_id","textbook_id","topic","mode","format","domain",
            "section","objective","provider","model","question",
            "screening","evidence","status","reviewer_notes","reviewed_by",
            "reviewed_at","created_at","updated_at")
    result = dict(zip(keys,row))
    for key in ("reviewed_at","created_at","updated_at"):
        if result[key] is not None:
            result[key] = result[key].isoformat()
    result["published"] = False
    return result
