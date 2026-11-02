"""Semantic duplicate candidate screening for v2.0.

Embeddings must be computed in a trusted backend and supplied by caller.
Similarity is a review flag, not a clinical equivalence determination.
"""
import math


def cosine(a, b):
    if not isinstance(a, (list, tuple)) or not isinstance(b, (list, tuple)) or not a or len(a) != len(b):
        raise ValueError("Embedding vectors must have equal nonzero dimensions")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in (*a, *b)):
        raise ValueError("Embedding vectors must be finite")
    aa = math.sqrt(sum(v * v for v in a))
    bb = math.sqrt(sum(v * v for v in b))
    if aa == 0 or bb == 0:
        raise ValueError("Zero-length embedding not allowed")
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / (aa * bb)))


def screen(candidate_vector, neighbors, threshold=0.85):
    if type(threshold) not in (int, float) or not 0 < threshold <= 1:
        raise ValueError("Invalid similarity threshold")
    if not isinstance(neighbors, list):
        raise ValueError("Neighbor list required")
    matches = []
    for neighbor in neighbors:
        similarity = cosine(candidate_vector, neighbor["embedding"])
        if similarity >= threshold:
            matches.append({"item_id": neighbor["item_id"], "similarity": round(similarity, 6)})
    return sorted(matches, key=lambda x: -x["similarity"])
