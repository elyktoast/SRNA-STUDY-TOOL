"""Bounded source lookups for a held MC option before its sole rewrite.

Uses the original owner, book and page/section scope. No model calls or writes.
"""
import re
from build_question_evidence import build_evidence


def supplement(conn, args, item, issues):
    flagged = set()
    for issue in issues:
        if issue.get("rule_id") not in ("R-2.4", "R-12.4"):
            continue
        match = re.fullmatch(r"(?:rationale\.distractor_breakdown|distractor_evidence)\.([A-D])",
                             issue.get("field", ""))
        option_id = match[1] if match else issue.get("option_id")
        if option_id in ("A", "B", "C", "D"):
            flagged.add(option_id)
    books = getattr(args, "textbook_ids", None) or [args.textbook_id]
    if not flagged or not all(books):
        return []
    existing = {citation.get("passage_id") for citation in item.get("evidence", [])
                if isinstance(citation, dict)}
    groups = []
    for option in item.get("options", []):
        if option.get("id") not in flagged or not isinstance(option.get("text"), str):
            continue
        by_book = []
        for book in books:
            packet = build_evidence(conn, args.owner_uid, option["text"], textbook_id=book, limit=2,
                                    section_id=args.section_id, include_subsections=args.include_subsections,
                                    page_start=args.page_start, page_end=args.page_end)
            by_book.append([p for p in packet["sources"] if p["textbook_id"] == book])
        groups.append([group[index] for index in range(2) for group in by_book if index < len(group)])
    result = []
    # Give each flagged option a chance at one new passage before taking a second.
    for index in range(max((len(group) for group in groups), default=0)):
        for group in groups:
            if index >= len(group):
                continue
            passage = group[index]
            if passage["passage_id"] in existing:
                continue
            existing.add(passage["passage_id"])
            result.append(passage)
            if len(result) == 4:
                return result
    return result
