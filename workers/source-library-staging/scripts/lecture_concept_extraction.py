"""Lecture text -> candidate concept extraction for private staging workflows.

Deterministic fallback only: headings and learning-objective lines are candidates,
not verified clinical concepts. No AI, network, storage or textbook citations.
"""
import re

HEADING = re.compile(r"^(?:#{1,4}\s+|(?:topic|section|unit|module)\s*\d*\s*[:.-]\s*)", re.I)
OBJECTIVE = re.compile(r"^(?:learning\s+)?objectives?\s*[:.-]\s*(.*)$", re.I)
BULLET = re.compile(r"^(?:[-*•]\s+|\d+[.)]\s+)")
PAGE = re.compile(r"^\s*(?:page|slide)\s+(\d+)\s*$", re.I)


def extract(text, *, max_concepts=60):
    if not isinstance(text, str) or not text.strip() or len(text) > 1_000_000:
        raise ValueError("Lecture text must be 1..1,000,000 characters")
    if type(max_concepts) is not int or not 1 <= max_concepts <= 100:
        raise ValueError("Invalid concept limit")
    candidates = []
    seen = set()
    locator = None
    in_objectives = False
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            in_objectives = False
            continue
        page = PAGE.fullmatch(line)
        if page:
            locator = "slide/page " + page.group(1)
            continue
        objective = OBJECTIVE.match(line)
        if objective:
            in_objectives = True
            line = objective.group(1).strip()
            if not line:
                continue
        elif HEADING.match(line):
            line = HEADING.sub("", line).strip()
            in_objectives = False
        elif in_objectives and BULLET.match(line):
            line = BULLET.sub("", line).strip()
        else:
            continue
        if not 5 <= len(line) <= 180 or len(line.split()) > 24:
            continue
        key = re.sub(r"\s+", " ", line.casefold())
        if key in seen:
            continue
        seen.add(key)
        candidates.append({"title": line, "lecture_locator": locator or ("line " + str(line_no)),
                           "objective": None, "importance": "standard"})
        if len(candidates) >= max_concepts:
            break
    return {"concepts": candidates, "requires_review": True,
            "extraction_method": "deterministic_heading_objective",
            "lecture_text_stored": False, "auto_generate": False}
