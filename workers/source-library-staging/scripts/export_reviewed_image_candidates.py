#!/usr/bin/env python3
"""Build reviewed, provenance-bound image candidates for future question generation.

This exports references only. It does not expose image pixels, publish textbook
content, or authorize generation without a separate access-control check.
"""
import argparse
import json
from pathlib import Path

from review_image_assets import validate_review, source_fingerprint


def approved_candidates(index_dir, review_path):
    index_dir, review_path = Path(index_dir), Path(review_path)
    review = json.loads(review_path.read_text(encoding="utf-8"))
    validate_review(index_dir, review)
    assets = json.loads((index_dir / "image_assets.json").read_text(encoding="utf-8"))
    links = json.loads((index_dir / "passage_image_links.json").read_text(encoding="utf-8"))
    approved = {d["asset_id"] for d in review["decisions"] if d["decision"] == "relevant"}
    by_id = {a["asset_id"]: a for a in assets}
    results = []
    for link in links:
        candidates = []
        for aid in link["candidate_asset_ids"]:
            if aid in approved:
                a = by_id[aid]
                if a["pdf_page"] != link["pdf_page"]:
                    raise ValueError("Cross-page candidate reference")
                candidates.append({"asset_id": aid, "pdf_page": a["pdf_page"],
                                   "bbox": a["bbox"]})
        if candidates:
            results.append({
                "chunk_index": link["chunk_index"],
                "pdf_page": link["pdf_page"],
                "candidate_assets": candidates,
                "association": "same_pdf_page_human_asset_reviewed",
                "semantic_match_verified": False,
            })
    return {
        "schema_version": 1,
        "source_sha256": source_fingerprint(index_dir),
        "passages": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--review", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.resolve() == args.review.resolve():
        parser.error("Output must not overwrite review decisions")
    result = approved_candidates(args.index, args.review)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"approved_passage_candidates": len(result["passages"])}))


if __name__ == "__main__":
    main()
