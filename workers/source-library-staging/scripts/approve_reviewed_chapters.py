#!/usr/bin/env python3
"""Trusted staging approval entrypoint; never accept a prebuilt plan from a client.

The caller must independently extract chapter candidates from the owner's
current private R2 PDF and authenticate/authorize the admin before invocation.
This function reconstructs every approved heading from trusted candidates.
"""
from approved_chapter_plan import build_plan
from apply_chapter_plan import apply_plan

def approve_reviewed_chapters(connection, owner_uid, textbook_id, groups,
                              review_decisions, selected_candidates, pdf_page_count):
    """Validate exact candidate selection then atomically assign sections.

    Does not approve citations, write source PDF content to logs, or perform
    browser authentication. The trusted server must supply groups and page_count.
    """
    plan = build_plan(groups, review_decisions, selected_candidates, pdf_page_count)
    result = apply_plan(connection, owner_uid, textbook_id, plan,
                        expected_fingerprint=plan["review_fingerprint"])
    return {**result, "review_fingerprint": plan["review_fingerprint"],
            "status": "sections_assigned_unverified_citations"}
