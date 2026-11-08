"""Optional staging-only semantic screening bridge for generated drafts.

The embedding provider is never invoked until the generator has produced a
schema-valid draft. A complete reconciled canonical index is required first.
No import, publication or provider call happens during factory construction.
"""
import json
import math
import urllib.request
from pathlib import Path

from item_semantic_inventory_reconcile_v2 import load_inventory, reconcile
from item_semantic_index_db_v2 import lookup
from item_ai_https_transport_v2 import _NoRedirect


def make_gemini_embed(*, api_key, model, enabled, opener=None):
    if enabled is not True:
        raise ValueError("Semantic embedding calls require explicit opt-in")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("Missing embedding provider credential")
    if model != "gemini-embedding-001":
        raise ValueError("Unsupported embedding model")
    endpoint = ("https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-embedding-001:embedContent")
    client = opener if opener is not None else urllib.request.build_opener(_NoRedirect())

    def embed(stem):
        if not isinstance(stem, str) or not stem.strip() or len(stem) > 10000:
            raise ValueError("Invalid embedding input")
        payload = {"model": "models/gemini-embedding-001",
                   "content": {"parts": [{"text": stem}]},
                   "taskType": "SEMANTIC_SIMILARITY"}
        data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint, data=data, method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key})
        with client.open(request, timeout=25) as response:
            if response.geturl() != endpoint:
                raise ValueError("Embedding endpoint redirected")
            raw = response.read(1048577)
            if len(raw) > 1048576:
                raise ValueError("Embedding response too large")
        parsed = json.loads(raw)
        vector = parsed.get("embedding", {}).get("values") if isinstance(parsed, dict) else None
        if (not isinstance(vector, list) or not 2 <= len(vector) <= 4096
                or any(type(v) not in (int, float) or not math.isfinite(v)
                       or abs(v) > 1e100 for v in vector)
                or not any(v != 0 for v in vector)):
            raise ValueError("Invalid embedding provider response")
        return vector
    return embed


def build_semantic_lookup(conn, *, owner_uid, env, embed):
    """Return None when disabled; otherwise fail closed on incomplete indexes."""
    if (env.get("STAGING_ONLY") != "true"
            or env.get("AI_GENERATION_OPT_IN") != "true"
            or env.get("AI_SEMANTIC_EMBEDDING_OPT_IN") != "true"):
        return None
    configured_owner = env.get("SEMANTIC_INDEX_OWNER_UID")
    if not configured_owner or configured_owner != owner_uid:
        raise ValueError("Semantic index owner mismatch")
    model = env.get("SEMANTIC_INDEX_EMBEDDING_MODEL")
    path = env.get("SEMANTIC_INDEX_INVENTORY_PATH")
    if model != "gemini-embedding-001" or not path:
        raise ValueError("Semantic index model or inventory unavailable")
    inventory, digest = load_inventory(path)
    result = reconcile(conn, owner_uid=owner_uid, embedding_model=model,
                       inventory=inventory)
    if not result["ready"]:
        # Do not call embedding provider or falsely report complete coverage.
        return None
    return lookup(conn, owner_uid=owner_uid, embedding_model=model,
                  embed=embed, index_ready=True,
                  expected_item_ids=set(inventory), expected_stem_hashes=inventory)
