"""Local staging-only, resumable embedding backfill. No automatic network calls.

The private canonical stem export is the sole input. Progress is stored as
private append-only JSONL, fsynced after every successful embedding. A completed
bundle can be passed to import_semantic_index_v2.py for separate approval.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


MODEL = "gemini-embedding-001"
MAX_ITEMS = 10000


def load_source(path):
    source = json.loads(Path(path).read_text(encoding="utf-8"))
    if (not isinstance(source, dict)
            or set(source) != {"schema_version", "inventory_digest", "item_count", "entries", "stems"}
            or source["schema_version"] != 1
            or not isinstance(source["entries"], list)
            or not isinstance(source["stems"], list)
            or not 1 <= len(source["entries"]) <= MAX_ITEMS
            or source["item_count"] != len(source["entries"])
            or len(source["stems"]) != len(source["entries"])):
        raise ValueError("Invalid private canonical source")
    digest = hashlib.sha256(json.dumps(source["entries"], separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if digest != source["inventory_digest"]:
        raise ValueError("Canonical inventory digest mismatch")
    stems = {}
    for entry, item in zip(source["entries"], source["stems"]):
        if (not isinstance(entry, dict) or set(entry) != {"item_id", "stem_hash"}
                or not isinstance(item, dict) or set(item) != {"item_id", "stem"}
                or item["item_id"] != entry["item_id"]
                or not isinstance(item["stem"], str) or not item["stem"].strip()
                or hashlib.sha256(item["stem"].encode()).hexdigest() != entry["stem_hash"]
                or item["item_id"] in stems):
            raise ValueError("Canonical stems and hashes mismatch")
        stems[item["item_id"]] = item["stem"]
    return source, stems


def load_progress(path, entries, *, digest=None, model=MODEL):
    expected = {e["item_id"]: e["stem_hash"] for e in entries}
    found = {}
    if not Path(path).exists():
        return found
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines:
        raise ValueError("Empty checkpoint file")
    header = json.loads(lines[0])
    if (not isinstance(header, dict)
            or header.get("schema_version") != 1
            or header.get("embedding_model") != model
            or (digest is not None and header.get("inventory_digest") != digest)
            or set(header) != {"schema_version", "embedding_model", "inventory_digest"}):
        raise ValueError("Checkpoint model or inventory mismatch")
    for line in lines[1:]:
        record = json.loads(line)
        if (not isinstance(record, dict)
                or set(record) != {"item_id", "stem_hash", "embedding"}
                or record["item_id"] not in expected
                or record["item_id"] in found
                or record["stem_hash"] != expected[record["item_id"]]):
            raise ValueError("Invalid or stale progress file")
        found[record["item_id"]] = record
    return found


def backfill(source_path, progress_path, output_path, *, embed, max_new=25):
    if not callable(embed) or type(max_new) is not int or not 0 <= max_new <= MAX_ITEMS:
        raise ValueError("Invalid backfill configuration")
    source, stems = load_source(source_path)
    progress = load_progress(progress_path, source["entries"], digest=source["inventory_digest"])
    # Validate all recovered vectors and their dimensions before any new calls.
    if progress:
        # Partial bundles cannot use the full-inventory importer; validate each
        # vector using the same bounded cosine rules as the live index.
        from item_semantic_duplicates import cosine
        dimension = None
        for record in progress.values():
            vector = record["embedding"]
            if not isinstance(vector, list) or not 2 <= len(vector) <= 4096:
                raise ValueError("Invalid recovered vector")
            if any(type(x) not in (int, float) or abs(x) > 1e100 for x in vector):
                raise ValueError("Invalid recovered vector")
            cosine(vector, vector)
            if dimension is None:
                dimension = len(vector)
            elif dimension != len(vector):
                raise ValueError("Mixed recovered dimensions")
    else:
        dimension = None
    if Path(output_path).exists():
        raise ValueError("Output already exists")
    added = 0
    if max_new:
        # Exclusive create on first use, then append. Never replace checkpoints.
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        descriptor = os.open(progress_path, flags, 0o600)
        try:
            with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
                if stream.tell() == 0:
                    stream.write(json.dumps({
                        "schema_version": 1,
                        "embedding_model": MODEL,
                        "inventory_digest": source["inventory_digest"]
                    }, separators=(",", ":")) + "\\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                for entry in source["entries"]:
                    if entry["item_id"] in progress or added >= max_new:
                        continue
                    vector = embed(stems[entry["item_id"]])
                    from item_semantic_duplicates import cosine
                    if (not isinstance(vector, list) or not 2 <= len(vector) <= 4096
                            or any(type(x) not in (int, float) or abs(x) > 1e100 for x in vector)):
                        raise ValueError("Invalid generated embedding")
                    cosine(vector, vector)
                    if dimension is None:
                        dimension = len(vector)
                    elif len(vector) != dimension:
                        raise ValueError("Mixed generated dimensions")
                    record = {**entry, "embedding": vector}
                    stream.write(json.dumps(record, allow_nan=False, separators=(",", ":")) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                    progress[entry["item_id"]] = record
                    added += 1
        except BaseException:
            raise
    complete = len(progress) == len(source["entries"])
    if complete:
        bundle = {"schema_version": 1, "inventory_digest": source["inventory_digest"],
                  "embedding_model": MODEL,
                  "entries": [progress[e["item_id"]] for e in source["entries"]]}
        # Write exclusive and verify using the exact staging importer validation.
        with open(output_path, "x", encoding="utf-8") as stream:
            os.chmod(output_path, 0o600)
            json.dump(bundle, stream, separators=(",", ":"), allow_nan=False)
            stream.write("\n")
        # A separate canonical inventory file is still required at import time.
    return {"complete": complete, "indexed": len(progress),
            "expected": len(source["entries"]), "new_calls": added,
            "output_created": complete}


def main(argv=None, env=None):
    env = os.environ if env is None else env
    parser = argparse.ArgumentParser()
    parser.add_argument("private_source")
    parser.add_argument("progress_jsonl")
    parser.add_argument("output_bundle")
    parser.add_argument("--max-new", type=int, default=25)
    args = parser.parse_args(argv)
    try:
        if (env.get("STAGING_ONLY") != "true"
                or env.get("AI_SEMANTIC_EMBEDDING_OPT_IN") != "true"
                or env.get("SEMANTIC_INDEX_EMBEDDING_MODEL") != MODEL):
            raise ValueError("Explicit staging embedding opt-in required")
        from item_semantic_live_bridge_v2 import make_gemini_embed
        embed = make_gemini_embed(api_key=env.get("AI_SEMANTIC_GEMINI_API_KEY", ""),
                                  model=MODEL, enabled=True)
        result = backfill(args.private_source, args.progress_jsonl, args.output_bundle,
                          embed=embed, max_new=args.max_new)
        print(json.dumps({"ok": True, **result}))
        return 0
    except Exception:
        print(json.dumps({"ok": False, "error": "BACKFILL_UNAVAILABLE"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
