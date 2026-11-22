"""Semantic duplicate candidate screening for v2.0.

Embeddings must be computed in a trusted backend and supplied by caller.
Similarity is a review flag, not a clinical equivalence determination.
"""
from array import array
import math


def _norm(vector):
    if (not isinstance(vector, (list, tuple, array)) or not vector
            or any(type(value) not in (int, float) or not math.isfinite(value) for value in vector)):
        raise ValueError("Embedding vectors must be finite nonempty numeric vectors")
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0 or not math.isfinite(norm):
        raise ValueError("Embedding norm must be finite and nonzero")
    return norm


def _similarity(a, b, a_norm, b_norm):
    scale = a_norm * b_norm
    if not math.isfinite(scale) or scale == 0:
        raise ValueError("Invalid embedding scale")
    return max(-1.0, min(1.0, sum(x * y for x, y in zip(a, b)) / scale))


def cosine(a, b):
    a_norm, b_norm = _norm(a), _norm(b)
    if len(a) != len(b):
        raise ValueError("Embedding vectors must have equal nonzero dimensions")
    return _similarity(a, b, a_norm, b_norm)


def screen(candidate_vector, neighbors, threshold=0.85):
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold <= 1:
        raise ValueError("Invalid similarity threshold")
    if not isinstance(neighbors, list):
        raise ValueError("Neighbor list required")
    # Validate the candidate even when the index returns no neighbors.
    candidate_norm = _norm(candidate_vector)
    matches = []
    seen = set()
    for neighbor in neighbors:
        if not isinstance(neighbor, dict) or not isinstance(neighbor.get("item_id"), str) or not neighbor["item_id"].strip():
            raise ValueError("Each semantic neighbor needs a stable item ID")
        if neighbor["item_id"] in seen:
            raise ValueError("Duplicate semantic neighbor ID")
        seen.add(neighbor["item_id"])
        vector = neighbor.get("embedding")
        norm = _norm(vector)
        if len(candidate_vector) != len(vector):
            raise ValueError("Embedding vectors must have equal nonzero dimensions")
        similarity = _similarity(candidate_vector, vector, candidate_norm, norm)
        if similarity >= threshold:
            matches.append({"item_id": neighbor["item_id"], "similarity": round(similarity, 6)})
    return sorted(matches, key=lambda x: -x["similarity"])
