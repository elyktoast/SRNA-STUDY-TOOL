"""Lecture text -> candidate concept extraction for private staging workflows.

Deterministic fallback only: headings, objectives and nearby teaching points are candidates,
not verified clinical concepts. No AI, network, storage or textbook citations.
"""
import re

HEADING = re.compile(r"^(?:#{1,4}\s+|(?:topic|section|unit|module)\s*\d*\s*[:.-]\s*)", re.I)
OBJECTIVE = re.compile(r"^(?:learning\s+)?objectives?(?:\s*[:.-]\s*(.*)|\s*)$", re.I)
BULLET = re.compile(r"^(?:[-*•]\s+|\d+[.)]\s+)")
EMPHASIS = re.compile(r"^Lecture (highlighted|bold):\s*(.+)$")
PRIORITY = {"learning_objective": 0, "highlighted": 1, "bold": 2, "standard": 3}
PAGE = re.compile(r"^\s*(?:page|slide)\s+(\d+)\s*:?\s*$", re.I)
DATE_HEADER = re.compile(r"^(?:(?:0?[1-9]|1[0-2])/(?:0?[1-9]|[12]\d|3[01])/(?:\d{2}|\d{4})|\d{4}-\d{2}-\d{2})$")


def _attach_learning_points(text, concepts):
    """Keep bounded slide-local scope cues, never treat them as evidence."""
    normalize = lambda value: re.sub(r"\s+", " ", value.strip().casefold())
    known = {normalize(c["title"]): c for c in concepts}
    points = {}
    active, pending = None, []
    def flush():
        if active and pending:
            point = " ".join(pending).strip()
            group = points.setdefault(active, [])
            if (12 <= len(point) <= 180 and 3 <= len(point.split()) <= 24
                    and point not in group and len(group) < 6):
                group.append(point)
        pending.clear()
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            flush()
            continue
        if PAGE.fullmatch(line) or DATE_HEADER.fullmatch(line) or re.fullmatch(r"\d{1,4}", line):
            flush(); active = None
            continue
        if EMPHASIS.fullmatch(line) or OBJECTIVE.fullmatch(line):
            flush(); active = None
            continue
        title = normalize(HEADING.sub("", line).strip())
        if not BULLET.match(line) and title in known:
            flush(); active = title
            continue
        if BULLET.match(line):
            flush()
            if active:
                pending.append(BULLET.sub("", line).strip())
            continue
        if re.match(r"(?:image\s+via|figure\b|copyright\b|https?://)", line, re.I):
            flush(); active = None
            continue
        if pending:
            pending.append(line)
    flush()
    for key, group in points.items():
        known[key]["learning_points"] = group


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
        if at_page_start and (DATE_HEADER.fullmatch(line) or re.fullmatch(r"\d{1,4}", line)):
            # PDF exports often put a date and page counter before the title.
            # Keep looking for the actual heading instead of planning a date.
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
    _attach_learning_points(text, ordered)
    return {"concepts": ordered[:max_concepts], "requires_review": True,
            "extraction_method": "deterministic_heading_objective",
            "lecture_text_stored": False, "auto_generate": False}
