#!/usr/bin/env python3
"""Group unverified chapter candidates for human review, without approving them.

Grouping is not deduplication: all source candidates remain visible in the
returned review groups. No textbook content is logged by the R2 audit.
"""
import re
import hashlib
import json

def normalize_heading(heading):
    return re.sub(r"[^a-z0-9]+", " ", heading.casefold()).strip()

def review_groups(text_candidates, layout_candidates):
    records = []
    for method, items in (("text", text_candidates), ("layout", layout_candidates)):
        for item in items:
            page = item["pdf_page"]
            if type(page) is not int or page < 1 or not isinstance(item.get("heading"), str):
                raise ValueError("Invalid chapter candidate")
            records.append({"pdf_page": page, "heading": item["heading"],
                            "detector": method, "review_required": True})
    records.sort(key=lambda x: (x["pdf_page"], x["detector"], x["heading"]))
    groups = []
    for candidate in records:
        if groups and candidate["pdf_page"] - groups[-1]["last_page"] <= 1:
            group = groups[-1]
            group["candidates"].append(candidate)
            group["last_page"] = candidate["pdf_page"]
        else:
            groups.append({"first_page": candidate["pdf_page"], "last_page": candidate["pdf_page"],
                           "candidates": [candidate], "review_required": True})
    for group in groups:
        group["detectors"] = sorted({c["detector"] for c in group["candidates"]})
        group["duplicate_heading_count"] = len(group["candidates"]) - len({
            (c["pdf_page"], normalize_heading(c["heading"])) for c in group["candidates"]})
        group["status"] = "needs_human_review"
    return groups

def public_review_summary(groups):
    """Safe for CI logs: no headings or textbook text."""
    return {"review_group_count": len(groups),
            "review_group_page_ranges": [[g["first_page"], g["last_page"]] for g in groups],
            "groups_with_both_detectors": sum(len(g["detectors"]) == 2 for g in groups),
            "review_required": True, "sections_approved": 0}

def review_fingerprint(groups):
    """Bind decisions to exact detected candidates, not mutable group numbers."""
    evidence = [
        {"first_page": g["first_page"], "last_page": g["last_page"],
         "candidates": [{"pdf_page": c["pdf_page"], "heading": c["heading"],
                         "detector": c["detector"]} for c in g["candidates"]]}
        for g in groups
    ]
    canonical = json.dumps(evidence, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
