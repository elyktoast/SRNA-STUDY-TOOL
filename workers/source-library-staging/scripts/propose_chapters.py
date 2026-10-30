#!/usr/bin/env python3
"""Propose (never auto-approve) chapter boundaries from extracted PDF page text.

Operates offline on pages.jsonl; emits a review-only JSON report. Does not
change sections.jsonl, citations, or the staging database.
"""
import argparse
import json
import re
from pathlib import Path

CHAPTER = re.compile(r"^\s*(?:chapter|chap\.)\s+(\d{1,3}|[IVXLCDM]{1,12})\s*[:.\-–]?\s*(.{0,110})$", re.I)
MAX_HEADING = 120


def propose(pages):
    candidates = []
    seen = set()
    for record in pages:
        page = record["pdf_page"]
        lines = [line.strip() for line in record.get("text", "").splitlines() if line.strip()]
        # Look near the start of the page only; do not mistake body references
        # such as "see Chapter 5" for a chapter heading.
        for line in lines[:12]:
            if len(line) > MAX_HEADING:
                continue
            match = CHAPTER.fullmatch(line)
            if not match:
                continue
            heading = line.strip()
            key = (match.group(1).lower(), heading.casefold())
            if key in seen:
                continue
            seen.add(key)
            candidates.append({"pdf_page": page, "heading": heading,
                               "source": "unverified_text_heuristic",
                               "review_required": True})
            break
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path, help="Local extraction folder with pages.jsonl")
    parser.add_argument("--out", type=Path, required=True, help="Review-only JSON output")
    args = parser.parse_args()
    if args.out.resolve() == (args.folder / "sections.jsonl").resolve():
        parser.error("Cannot overwrite approved section input")
    pages = [json.loads(line) for line in (args.folder / "pages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(type(p.get("pdf_page")) is not int or p["pdf_page"] < 1 or not isinstance(p.get("text"), str) for p in pages):
        parser.error("Invalid extracted page records")
    result = {"status": "review_only", "citation_verified": False,
              "candidates": propose(pages)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "review_only", "candidate_count": len(result["candidates"])}))


if __name__ == "__main__":
    main()
