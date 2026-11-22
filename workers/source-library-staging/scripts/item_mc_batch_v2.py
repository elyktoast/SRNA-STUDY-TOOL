"""Private staging MC batch authentication and draft neighbor lookup."""
import hashlib
import hmac
import json
import time
from collections import OrderedDict
from threading import Lock
from uuid import UUID

from item_cloudflare_embeddings_v2 import batch_fits, make_embed_many, valid_vector
from source_review_roles_supabase_v2 import ProtectedReviewerRoleStore


def authenticate(environ, action, secret, conn_factory):
    if environ.get("REQUEST_METHOD") != "POST" or not isinstance(secret, str) or len(secret) < 32:
        raise ValueError("Batch authentication required")
    owner = str(UUID(environ.get("HTTP_X_BATCH_OWNER", "")))
    timestamp = environ.get("HTTP_X_BATCH_TIME", "")
    length = int(environ.get("CONTENT_LENGTH", "0"))
    if not timestamp.isascii() or not timestamp.isdigit() or len(timestamp) > 12:
        raise ValueError("Invalid batch time")
    if abs(time.time() - int(timestamp)) > 90 or not 1 <= length <= 16384:
        raise ValueError("Invalid batch envelope")
    body = environ["wsgi.input"].read(length)
    prefix = f"srna-mc-batch-v1\n{action}\n{owner}\n{timestamp}\n".encode()
    signature = hmac.new(secret.encode(), prefix + body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, environ.get("HTTP_X_BATCH_SIGNATURE", "")):
        raise ValueError("Invalid batch signature")
    with conn_factory() as conn:
        if not ProtectedReviewerRoleStore(conn).is_active_admin(owner):
            raise ValueError("Batch administrator required")
    return owner, json.loads(body)


def prior_ids(values):
    if not isinstance(values, list) or len(values) > 99:
        raise ValueError("Invalid prior drafts")
    ids = [str(UUID(value)) for value in values]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate prior draft ID")
    return ids


_vector_cache = OrderedDict()
_vector_cache_lock = Lock()
_VECTOR_CACHE_LIMIT = 256


def _embed_stems(owner, secret, stems):
    """Fetch unique cache misses in bounded provider requests."""
    vectors = {}
    missing = []
    with _vector_cache_lock:
        for stem in dict.fromkeys(stems):
            key = (owner, stem)
            if key in _vector_cache:
                vectors[stem] = _vector_cache[key]
                _vector_cache.move_to_end(key)
            else:
                if not batch_fits([stem]):
                    raise ValueError("Invalid batch draft stem")
                missing.append(stem)
    if not missing:
        return vectors
    embed = make_embed_many(enabled=True, relay_secret=secret)
    start = 0
    while start < len(missing):
        end = start + 1
        while end < len(missing) and batch_fits(missing[start:end + 1]):
            end += 1
        texts = missing[start:end]
        result = embed(texts)
        if len(result) != len(texts) or any(not valid_vector(vector) for vector in result):
            raise ValueError("Invalid batch draft embeddings")
        with _vector_cache_lock:
            for stem, vector in zip(texts, result):
                vectors[stem] = _vector_cache[owner, stem] = tuple(vector)
                _vector_cache.move_to_end((owner, stem))
            while len(_vector_cache) > _VECTOR_CACHE_LIMIT:
                _vector_cache.popitem(last=False)
        start = end
    return vectors


def with_draft_neighbors(lookup, conn, owner, ids, secret):
    if lookup is None:
        raise ValueError("Complete semantic index required for MC batches")
    if not ids:
        return lookup
    with conn.cursor() as cur:
        cur.execute("""
            select id::text, question_json->>'item_id', question_json->>'stem'
            from source_library_staging.generated_question_drafts_v2
            where owner_uid=%s::uuid and id=any(%s::uuid[])
        """, (owner, ids))
        rows = cur.fetchall()
    if {row[0] for row in rows} != set(ids) or any(not item_id or not stem for _, item_id, stem in rows):
        raise ValueError("Batch draft comparison unavailable")

    def compare(item):
        result = lookup(item)
        prior = [(item_id, stem) for _, item_id, stem in rows if item_id != item["item_id"]]
        vectors = _embed_stems(owner, secret, [stem for _, stem in prior])
        return {**result, "neighbors": [
            *result["neighbors"],
            *({"item_id": item_id, "embedding": vectors[stem]} for item_id, stem in prior),
        ]}
    return compare
