"""Lecture text -> candidate concept extraction for private staging workflows.

Deterministic fallback only: headings and learning-objective lines are candidates,
not verified clinical concepts. No AI, network, storage or textbook citations.
"""
import re

HEADING = re.compile(r"^(?:#{1,4}\s+|(?:topic|section|unit|module)\s*\d*\s*[:.-]\s*)", re.I)
OBJECTIVE = re.compile(r"^(?:learning\s+)?objectives?(?:\s*[:.-]\s*(.*)|\s*)$", re.I)
BULLET = re.compile(r"^(?:[-*•]\s+|\d+[.)]\s+)")
EMPHASIS = re.compile(r"^Lecture (highlighted|bold):\s*(.+)$")
PRIORITY = {"learning_objective": 0, "highlighted": 1, "bold": 2, "standard": 3}
PAGE = re.compile(r"^\s*(?:page|slide)\s+(\d+)\s*:?\s*$", re.I)


def extract(text, *, max_concepts=60):
    if not isinstance(text, str) or not text.strip() or len(text) > 1_000_000:
        raise ValueError("Lecture text must be 1..1,000,000 characters")
    if type(max_concepts) is not int or not 1 <= max_concepts <= 100:
        raise ValueError("Invalid concept limit")
    candidates = {}
    locator = None
    in_objectives = False
    at_page_start = False
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            # Markdown commonly separates a heading from its bullet list.
            continue
        page = PAGE.fullmatch(line)
        if page:
            locator = "slide/page " + page.group(1)
            at_page_start = True
            in_objectives = False
            continue
        emphasized = EMPHASIS.fullmatch(line)
        if emphasized:
            importance, title = emphasized.groups()
            line = BULLET.sub("", title).strip(" *•")
        heading = bool(HEADING.match(line))
        if heading:
            line = HEADING.sub("", line).strip()
        objective = OBJECTIVE.fullmatch(line)
        if emphasized:
            in_objectives = False
        elif objective:
            in_objectives = True
            line = (objective.group(1) or "").strip()
            if not line:
                continue
        elif heading:
            in_objectives = False
        elif in_objectives and BULLET.match(line):
            line = BULLET.sub("", line).strip()
        elif at_page_start:
            # Slide title candidate, not a verified clinical fact.
            at_page_start = False
        else:
            in_objectives = False
            continue
        at_page_start = False
        if not 5 <= len(line) <= 180 or len(line.split()) > 24:
            continue
        key = re.sub(r"\s+", " ", line.casefold())
        importance = importance if emphasized else "learning_objective" if in_objectives else "standard"
        previous = candidates.get(key)
        if previous is None or PRIORITY[importance] < PRIORITY[previous["importance"]]:
            candidates[key] = {"title": line, "lecture_locator": locator or ("line " + str(line_no)),
                               "objective": None, "importance": importance}
    ordered = list(candidates.values())
    if any(c["importance"] in ("highlighted", "bold") for c in ordered):
        ordered.sort(key=lambda c: PRIORITY[c["importance"]])
    return {"concepts": ordered[:max_concepts], "requires_review": True,
            "extraction_method": "deterministic_heading_objective",
            "lecture_text_stored": False, "auto_generate": False}
