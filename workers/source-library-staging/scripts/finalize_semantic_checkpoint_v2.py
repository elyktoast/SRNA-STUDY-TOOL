"""Staging-only checkpoint finalizer for future authorized embedding batches.

Always validate the recovered checkpoint against the canonical inventory before
uploading an immutable encrypted snapshot. Never invokes an embedding provider.
"""
import argparse
import json
import os
import sys
from pathlib import Path

from backfill_semantic_embeddings_v2 import backfill, load_source, load_progress
from semantic_checkpoint_r2_v2 import transfer


def finalize(source_path, progress_path, output_path, snapshot, *, env=None,
             transport=transfer):
    env = os.environ if env is None else env
    if env.get("STAGING_ONLY") != "true":
        raise ValueError("Staging only")
    path = Path(progress_path)
    if not path.is_file() or path.stat().st_size == 0:
        return {"saved": False, "reason": "no_checkpoint"}
    source, _ = load_source(source_path)
    progress = load_progress(progress_path, source["entries"],
                             digest=source["inventory_digest"])
    # This validates vector values, lengths and dimensions without API calls.
    backfill(source_path, progress_path, output_path,
             embed=lambda _: (_ for _ in ()).throw(AssertionError("No API calls")),
             max_new=0, preflight=True)
    if not progress:
        return {"saved": False, "reason": "no_embeddings"}
    result = transport("save", progress_path, snapshot=snapshot, env=env)
    return {"saved": bool(result["saved"]), "indexed": len(progress),
            "expected": len(source["entries"])}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("private_source")
    parser.add_argument("progress_jsonl")
    parser.add_argument("output_bundle")
    parser.add_argument("--snapshot", required=True)
    args = parser.parse_args(argv)
    try:
        result = finalize(args.private_source, args.progress_jsonl,
                          args.output_bundle, args.snapshot)
        print(json.dumps({"ok": True, **result}))
        return 0
    except Exception:
        print(json.dumps({"ok": False, "error": "CHECKPOINT_FINALIZE_UNAVAILABLE"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
