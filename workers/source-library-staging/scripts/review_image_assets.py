#!/usr/bin/env python3
"""Create and validate local human-review decisions for PDF image assets.

No image bytes, textbook text, or credentials are written. Decisions are
explicitly human-supplied; a candidate page match is never auto-approved.
"""
import argparse
import hashlib
import json
from pathlib import Path

ALLOWED = {"pending", "relevant", "decorative", "needs_review"}


def source_fingerprint(index_dir):
    index_dir = Path(index_dir)
    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    digest = manifest.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ValueError("Invalid source digest")
    return digest


def create_review(index_dir):
    index_dir = Path(index_dir)
    assets = json.loads((index_dir / "image_assets.json").read_text(encoding="utf-8"))
    if not isinstance(assets, list):
        raise ValueError("Invalid asset catalog")
    ids = [a.get("asset_id") for a in assets if isinstance(a, dict)]
    if len(ids) != len(assets) or any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or duplicate image assets")
    return {
        "schema_version": 1,
        "source_sha256": source_fingerprint(index_dir),
        "decisions": [{"asset_id": aid, "decision": "pending", "notes": ""} for aid in ids],
    }


def validate_review(index_dir, review):
    expected = create_review(index_dir)
    if (not isinstance(review, dict) or review.get("schema_version") != 1
            or review.get("source_sha256") != expected["source_sha256"]):
        raise ValueError("Stale or invalid review source")
    decisions = review.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(expected["decisions"]):
        raise ValueError("Incomplete image review")
    by_id = {}
    for item in decisions:
        if not isinstance(item, dict):
            raise ValueError("Invalid review entry")
        aid, decision, notes = item.get("asset_id"), item.get("decision"), item.get("notes")
        if (not isinstance(aid, str) or aid in by_id or decision not in ALLOWED
                or not isinstance(notes, str) or len(notes) > 1000):
            raise ValueError("Invalid image review decision")
        by_id[aid] = item
    if set(by_id) != {a["asset_id"] for a in expected["decisions"]}:
        raise ValueError("Image review references do not match catalog")
    return {"total": len(decisions), "reviewed": sum(i["decision"] != "pending" for i in decisions),
            "relevant": sum(i["decision"] == "relevant" for i in decisions),
            "pending": sum(i["decision"] == "pending" for i in decisions)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--init", action="store_true", help="Create pending decisions, never auto-approve")
    args = parser.parse_args()
    if args.init:
        if args.review.exists():
            parser.error("Review file already exists; refusing to overwrite decisions")
        args.review.parent.mkdir(parents=True, exist_ok=True)
        args.review.write_text(json.dumps(create_review(args.index), indent=2) + "\n", encoding="utf-8")
    summary = validate_review(args.index, json.loads(args.review.read_text(encoding="utf-8")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
