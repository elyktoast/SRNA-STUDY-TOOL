"""Private staging-only resumable generation checkpoints.

Call only from authenticated admin backend. Never expose intermediate JSON to
anonymous users or accept owner_uid from client input. Caller owns transaction.
"""
import hashlib
import json
from uuid import UUID


def fingerprint(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def load(conn, *, owner_uid, textbook_id, request_hash, evidence_hash):
    owner, book = str(UUID(str(owner_uid))), str(UUID(str(textbook_id)))
    with conn.cursor() as cur:
        cur.execute("""
          select c.stage,c.concept_card,c.draft
          from source_library_staging.generation_checkpoints_v2 c
          join source_library_staging.textbooks t on t.id=c.textbook_id
          where c.owner_uid=%s::uuid and c.textbook_id=%s::uuid
            and t.owner_uid=%s::uuid and t.status='ready'
            and c.request_hash=%s and c.evidence_hash=%s
            and c.status='pending' and c.expires_at>now()
        """, (owner, book, owner, request_hash, evidence_hash))
        row = cur.fetchone()
    if row is None:
        return None
    stage, concept, draft = row
    if stage not in ("concept_card", "draft") or not isinstance(concept, dict):
        raise ValueError("Invalid saved checkpoint")
    if stage == "draft" and not isinstance(draft, dict):
        raise ValueError("Invalid saved draft checkpoint")
    return {"concept_card": concept, **({"draft": draft} if stage == "draft" else {})}


def record(conn, *, owner_uid, textbook_id, request_hash, evidence_hash, stage, value):
    owner, book = str(UUID(str(owner_uid))), str(UUID(str(textbook_id)))
    if stage not in ("concept_card", "draft") or not isinstance(value, dict):
        raise ValueError("Invalid checkpoint stage or value")
    if not all(isinstance(h, str) and len(h) == 64 and all(ch in "0123456789abcdef" for ch in h)
               for h in (request_hash, evidence_hash)):
        raise ValueError("Invalid checkpoint fingerprint")
    # Atomic monotonic transition. A changed evidence hash never overwrites
    # an existing checkpoint; only the exact request and evidence can resume.
    with conn.cursor() as cur:
        if stage == "concept_card":
            cur.execute("""
              insert into source_library_staging.generation_checkpoints_v2
                (owner_uid,textbook_id,request_hash,evidence_hash,stage,concept_card)
              select t.owner_uid,t.id,%s,%s,'concept_card',%s::jsonb
              from source_library_staging.textbooks t
              where t.id=%s::uuid and t.owner_uid=%s::uuid and t.status='ready'
              on conflict (owner_uid,request_hash) do nothing
              returning id
            """, (request_hash,evidence_hash,json.dumps(value),book,owner))
        else:
            cur.execute("""
              update source_library_staging.generation_checkpoints_v2 c
              set stage='draft',draft=%s::jsonb,updated_at=now()
              from source_library_staging.textbooks t
              where c.textbook_id=t.id and t.owner_uid=%s::uuid
                and c.owner_uid=%s::uuid and c.textbook_id=%s::uuid
                and c.request_hash=%s and c.evidence_hash=%s
                and c.stage='concept_card' and c.status='pending'
                and c.expires_at>now()
              returning c.id
            """, (json.dumps(value),owner,owner,book,request_hash,evidence_hash))
        row = cur.fetchone()
    if row is None:
        raise ValueError("Checkpoint cannot be recorded or advanced")
    # Commit each stage immediately, so a later 429 does not roll it back.
    conn.commit()


def complete(conn, *, owner_uid, request_hash, evidence_hash):
    owner = str(UUID(str(owner_uid)))
    with conn.cursor() as cur:
        cur.execute("""
          update source_library_staging.generation_checkpoints_v2
          set status='completed',updated_at=now()
          where owner_uid=%s::uuid and request_hash=%s and evidence_hash=%s
            and status='pending' and expires_at>now()
        """, (owner,request_hash,evidence_hash))
    conn.commit()
