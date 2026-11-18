"""Private, durable admission and rewrite accounting for checkpointed generation.

An interrupted attempt cannot be replayed. Completed checkpoints remain the only
recovery path. Receipts contain identifiers/hashes, never question/source text.
"""
from contextlib import contextmanager
from uuid import UUID
from threading import Lock
import re


# Staging deploys one Gunicorn worker in one container. This nonblocking lock
# serializes paid work across its HTTP threads, without relying on session-level
# database locks (which are unsafe with transaction-pooling connections).
_active = Lock()


class GenerationAlreadyStarted(RuntimeError):
    pass


class GenerationBusy(RuntimeError):
    pass


def _identity(owner_uid, textbook_id, item_id, request_hash, evidence_hash):
    owner, book, item = (str(UUID(str(v))) for v in (owner_uid, textbook_id, item_id))
    if any(not isinstance(v, str) or re.fullmatch('[a-f0-9]{64}', v) is None
           for v in (request_hash, evidence_hash)):
        raise ValueError('Invalid generation attempt fingerprint')
    return owner, book, item, request_hash, evidence_hash


@contextmanager
def attempt(conn, *, owner_uid, textbook_id, item_id, request_hash, evidence_hash):
    owner, book, item, request, evidence = _identity(owner_uid, textbook_id, item_id, request_hash, evidence_hash)
    if not _active.acquire(blocking=False):
        raise GenerationBusy('Staging generation already active')
    try:
        with conn.cursor() as cur:
            cur.execute('''insert into source_library_staging.generation_attempts_v2
                (owner_uid,textbook_id,item_id,request_hash,evidence_hash)
                select t.owner_uid,t.id,%s::uuid,%s,%s
                from source_library_staging.textbooks t
                where t.owner_uid=%s::uuid and t.id=%s::uuid and t.status='ready'
                on conflict (owner_uid,item_id) do nothing returning item_id''',
                (item, request, evidence, owner, book))
            claimed = cur.fetchone()
        conn.commit()  # Durable BEFORE the first paid call, including failures.
        if claimed is None:
            raise GenerationAlreadyStarted('Generation item already started; completed recovery only')
        yield
    finally:
        # Process death drops local active work; the durable receipt remains.
        _active.release()


def reserve_rewrite(conn, *, owner_uid, textbook_id, item_id, request_hash, evidence_hash):
    owner, book, item, request, evidence = _identity(owner_uid, textbook_id, item_id, request_hash, evidence_hash)
    with conn.cursor() as cur:
        cur.execute('''update source_library_staging.generation_attempts_v2
            set rewrite_reserved=true,rewrite_reserved_at=now()
            where owner_uid=%s::uuid and textbook_id=%s::uuid and item_id=%s::uuid
              and request_hash=%s and evidence_hash=%s and state='started'
              and rewrite_reserved=false returning item_id''',
            (owner, book, item, request, evidence))
        claimed = cur.fetchone()
    conn.commit()  # Ambiguous provider failures still consume the one rewrite.
    if claimed is None:
        raise GenerationAlreadyStarted('Rewrite already reserved or attempt unavailable')


def finish(conn, *, owner_uid, item_id):
    with conn.cursor() as cur:
        cur.execute('''update source_library_staging.generation_attempts_v2
            set state='completed',completed_at=now()
            where owner_uid=%s::uuid and item_id=%s::uuid and state='started'
            returning item_id''', (str(UUID(str(owner_uid))), str(UUID(str(item_id)))))
        if cur.fetchone() is None:
            raise GenerationAlreadyStarted('Generation attempt unavailable')
    conn.commit()
