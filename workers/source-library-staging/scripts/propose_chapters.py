#!/usr/bin/env python3
"""Conservative review-only chapter candidates from extracted PDF pages.

No section assignment, citation verification, or database writes.
"""
import argparse
import json
import re
from pathlib import Path

CHAPTER = re.compile(r"^(?:chapter|chap[.]?)\\s+([0-9]{1,3}|[IVXLCDM]{1,12})(?:\\s*[:.\\-–]\\s*|\\s+)(.{0,110})$", re.I)
CHAPTER_ONLY = re.compile(r"^(?:chapter|chap[.]?)\\s+([0-9]{1,3}|[IVXLCDM]{1,12})$", re.I)
NUMBER_ONLY = re.compile(r"^([0-9]{1,3}|[IVXLCDM]{1,8})$", re.I)
MAX_HEADING = 120
EXCLUDED_TITLES = {"contents", "references", "index", "bibliography", "appendix", "notes", "preface", "foreword"}
SENTENCE_END = re.compile(r"[.!?]$")
SENTENCE_START = re.compile(r"^(?:the|this|these|it|in|for|see|as|and|or|but|when|with)\\b", re.I)


def plausible_title(value):
    title = value.strip(" :-–")
    return (4 <= len(title) <= 105 and len(title.split()) <= 13
            and title.casefold() not in EXCLUDED_TITLES
            and not SENTENCE_END.search(title)
            and not SENTENCE_START.search(title)
            and bool(re.search(r"[A-Za-z]", title)))


def propose(pages):
    candidates, seen = [], set()
    for record in pages:
        page = record["pdf_page"]
        lines = [s.strip() for s in record.get("text", "").splitlines() if s.strip()]
        for index, line in enumerate(lines[:12]):
            if len(line) > MAX_HEADING:
                continue
            number, heading, method = None, None, None
            match = CHAPTER.fullmatch(line)
            if match and plausible_title(match.group(2)):
                number, heading, method = match.group(1), line, "explicit_chapter"
            else:
                match = CHAPTER_ONLY.fullmatch(line)
                if match and index + 1 < len(lines) and plausible_title(lines[index + 1]):
                    number, heading, method = match.group(1), line + " " + lines[index + 1], "split_chapter"
                elif index <= 5:
                    match = NUMBER_ONLY.fullmatch(line)
                    if match and index + 1 < len(lines) and plausible_title(lines[index + 1]):
                        number, heading, method = match.group(1), line + " " + lines[index + 1], "standalone_number"
            if number is None:
                continue
            key = (number.casefold(), heading.casefold())
            if key not in seen:
                seen.add(key)
                candidates.append({"pdf_page": page, "heading": heading,
                                   "source": "unverified_text_heuristic", "method": method,
                                   "review_required": True})
            break
    return candidates


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.resolve() == (args.folder / "sections.jsonl").resolve():
        parser.error("Cannot overwrite approved section input")
    pages = [json.loads(line) for line in (args.folder / "pages.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    if any(type(p.get("pdf_page")) is not int or p["pdf_page"] < 1 or not isinstance(p.get("text"), str) for p in pages):
        parser.error("Invalid extracted page records")
    result = {"status": "review_only", "citation_verified": False, "candidates": propose(pages)}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "review_only", "candidate_count": len(result["candidates"])}))


if __name__ == "__main__":
    main()
