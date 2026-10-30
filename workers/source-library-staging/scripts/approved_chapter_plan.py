#!/usr/bin/env python3
"""Prepare an explicit chapter assignment plan; no database writes.

A review group's classification is not sufficient to identify a chapter title
or exact boundary. Require the reviewer to select a specific detected heading.
"""
from chapter_review import review_fingerprint
from validate_chapter_decisions import validate_decisions

def build_plan(groups, payload, selections, pdf_page_count):
    """Return a checked, uncommitted plan tied to candidate evidence."""
    validated = validate_decisions(payload, groups)
    if type(pdf_page_count) is not int or pdf_page_count < 1:
        raise ValueError("Invalid PDF page count")
    if not isinstance(selections, list):
        raise ValueError("Explicit chapter selections required")
    wanted = [d for d in validated["decisions"] if d["decision"] in ("Chapter", "Subsection")]
    if len(selections) != len(wanted):
        raise ValueError("One explicit heading selection required for each accepted group")
    sections = []
    previous_page = 0
    for decision, selected in zip(wanted, selections):
        if not isinstance(selected, dict) or type(selected.get("group")) is not int or selected["group"] != decision["group"]:
            raise ValueError("Chapter selection group mismatch")
        group = groups[selected["group"] - 1]
        index = selected.get("candidate_index")
        if type(index) is not int or not 0 <= index < len(group["candidates"]):
            raise ValueError("Invalid candidate index")
        candidate = group["candidates"][index]
        page, heading = candidate["pdf_page"], candidate["heading"]
        if not 1 <= page <= pdf_page_count or page <= previous_page:
            raise ValueError("Chapter boundaries must be strictly increasing")
        if not isinstance(heading, str) or not heading.strip() or len(heading) > 500:
            raise ValueError("Invalid selected chapter heading")
        kind = decision["decision"]
        if kind == "Subsection" and not any(s["kind"] == "Chapter" for s in sections):
            raise ValueError("Subsection requires an earlier chapter")
        sections.append({"kind": kind, "heading": heading, "start_page": page,
                         "group": selected["group"], "detector": candidate["detector"]})
        previous_page = page
    return {"status": "prepared_not_applied", "review_fingerprint": review_fingerprint(groups),
            "sections": sections, "citation_verified": False, "database_written": False}
