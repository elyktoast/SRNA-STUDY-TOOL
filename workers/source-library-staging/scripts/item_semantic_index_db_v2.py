"""Trusted staging-only semantic index lookup.

No writes or provider calls. Caller supplies a trusted embedding function;
a partial or absent index is never reported as a completed search.
"""
from uuid import UUID
from item_semantic_duplicates import cosine

MAX_ROWS = 5000

def lookup(conn, *, owner_uid, embedding_model, embed, index_ready):
    if index_ready is not True:
        raise ValueError("Semantic index not verified")
    owner = str(UUID(owner_uid))
    if not isinstance(embedding_model, str) or not embedding_model.strip() or not callable(embed):
        raise ValueError("Trusted embedding configuration required")

    def semantic_lookup(item):
        if not isinstance(item, dict) or not isinstance(item.get("stem"), str) or not item["stem"].strip():
            raise ValueError("Question stem required")
        vector = embed(item["stem"])
        cosine(vector, vector)
        with conn.cursor() as cur:
            cur.execute(
                """select item_id, embedding from source_library_staging.question_semantic_index_v2
                   where owner_uid=%s and embedding_model=%s and item_id<>%s
                   order by item_id limit %s""",
                (owner, embedding_model, item.get("item_id", ""), MAX_ROWS + 1))
            rows = cur.fetchall()
        if len(rows) > MAX_ROWS:
            raise ValueError("Semantic index exceeds exhaustive search cap")
        neighbors = []
        for item_id, embedding in rows:
            neighbor = list(embedding)
            cosine(vector, neighbor)
            neighbors.append({"item_id": item_id, "embedding": neighbor})
        return {"embedding": vector, "neighbors": neighbors,
                "search_complete": True, "index_id": "question_semantic_index_v2:" + embedding_model}
    return semantic_lookup
