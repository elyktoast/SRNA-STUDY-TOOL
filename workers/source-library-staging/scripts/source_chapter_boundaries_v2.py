"""Validate human-verified chapter boundaries before associating indexed passages.

This module does not infer headings from OCR, extract textbook content, or write to DB.
Physical PDF pages are 1-based; printed textbook pages are not assumed equal.
"""


def validate_chapter_boundaries(boundaries, *, pdf_page_count):
    if type(pdf_page_count) is not int or pdf_page_count < 1:
        raise ValueError("Invalid PDF page count")
    if not isinstance(boundaries, list) or not boundaries:
        raise ValueError("At least one reviewed chapter boundary required")
    if len(boundaries) > 2000:
        raise ValueError("Excessive chapter count")
    approved = []
    previous = 0
    for item in boundaries:
        if not isinstance(item, dict) or set(item) != {"heading", "start_page", "verified_against_pdf"}:
            raise ValueError("Invalid chapter boundary structure")
        heading, start, reviewed = item["heading"], item["start_page"], item["verified_against_pdf"]
        if not isinstance(heading, str) or not heading.strip() or len(heading) > 240:
            raise ValueError("Invalid chapter heading")
        if type(start) is not int or not previous < start <= pdf_page_count:
            raise ValueError("Chapter pages must be strictly increasing physical PDF pages")
        if reviewed is not True:
            raise ValueError("Chapter boundary requires explicit source verification")
        approved.append({"heading": heading.strip(), "start_page": start,
                         "verified_against_pdf": True})
        previous = start
    return approved


def assign_passages_to_chapters(passages, boundaries, *, pdf_page_count):
    """Return chapter indexes; pages before first reviewed boundary stay unassigned."""
    reviewed = validate_chapter_boundaries(boundaries, pdf_page_count=pdf_page_count)
    if not isinstance(passages, list):
        raise ValueError("Invalid passage list")
    result = []
    for p in passages:
        if not isinstance(p, dict):
            raise ValueError("Invalid passage")
        start, end = p.get("page_start"), p.get("page_end")
        if (type(start) is not int or type(end) is not int
                or not 1 <= start <= end <= pdf_page_count):
            raise ValueError("Invalid passage page reference")
        matching = [i for i, item in enumerate(reviewed) if item["start_page"] <= start]
        chapter_index = matching[-1] if matching else None
        # Cross-boundary chunks are ambiguous; do not silently attach them.
        if chapter_index is not None and chapter_index + 1 < len(reviewed):
            if end >= reviewed[chapter_index + 1]["start_page"]:
                chapter_index = None
        result.append(chapter_index)
    return result
