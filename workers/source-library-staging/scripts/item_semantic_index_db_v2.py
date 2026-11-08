"""Trusted staging-only semantic index lookup.

No writes or provider calls. Caller supplies a trusted embedding function;
a partial or absent index is never reported as a completed search.
"""
from uuid import UUID
from item_semantic_duplicates import cosine

MAX_ROWS = 5000

def lookup(conn, *, owner_uid, embedding_model, embed, index_ready, expected_item_ids=None):
    if index_ready is not True:
        raise ValueError("Semantic index not verified")
    if (not isinstance(expected_item_ids, (set, frozenset)) or not expected_item_ids
            or not all(isinstance(x, str) and x.strip() for x in expected_item_ids)
            or len(expected_item_ids) > MAX_ROWS):
        raise ValueError("Complete canonical item inventory required")
    expected_item_ids = frozenset(expected_item_ids)
    owner = str(UUID(owner_uid))
    if not isinstance(embedding_model, str) or not embedding_model.strip() or not callable(embed):
        raise ValueError("Trusted embedding configuration required")

    def semantic_lookup(item):
        if not isinstance(item, dict) or not isinstance(item.get("stem"), str) or not item["stem"].strip():
            raise ValueError("Question stem required")
        candidate_id = item.get("item_id")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            raise ValueError("Stable candidate item ID required")
        vector = embed(item["stem"])
        cosine(vector, vector)
        if len(vector) < 2 or len(vector) > 4096:
            raise ValueError("Invalid candidate embedding dimensions")
        with conn.cursor() as cur:
            cur.execute(
                """select item_id, embedding from source_library_staging.question_semantic_index_v2
                   where owner_uid=%s and embedding_model=%s and item_id<>%s
                   order by item_id limit %s""",
                (owner, embedding_model, candidate_id, MAX_ROWS + 1))
            rows = cur.fetchall()
        if len(rows) > MAX_ROWS:
            raise ValueError("Semantic index exceeds exhaustive search cap")
        returned_ids = [item_id for item_id, _ in rows]
        required_ids = expected_item_ids - {candidate_id}
        if (len(returned_ids) != len(set(returned_ids))
                or set(returned_ids) != required_ids):
            raise ValueError("Semantic index coverage does not match canonical item inventory")
        neighbors = []
        for item_id, embedding in rows:
            if not isinstance(embedding, (list, tuple)):
                raise ValueError("Invalid indexed embedding")
            neighbor = list(embedding)
            cosine(vector, neighbor)
            neighbors.append({"item_id": item_id, "embedding": neighbor})
        return {"embedding": vector, "neighbors": neighbors,
                "search_complete": True, "index_id": "question_semantic_index_v2:" + embedding_model}
    return semantic_lookup
