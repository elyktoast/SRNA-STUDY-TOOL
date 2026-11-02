"""Deterministic exact-normalized duplicate detection for new item drafts."""
import hashlib
import re


def stem_fingerprint(stem):
    if not isinstance(stem, str) or not stem.strip():
        raise ValueError("A nonempty stem is required")
    normalized = re.sub(r"[^a-z0-9]+", " ", stem.casefold()).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def detect(item, known_stems=()):
    candidate = stem_fingerprint(item["stem"])
    if any(stem_fingerprint(stem) == candidate for stem in known_stems):
        return [{"rule_id": "R-11", "message": "Duplicate normalized stem"}]
    return []
