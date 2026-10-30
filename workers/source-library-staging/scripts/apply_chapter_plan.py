#!/usr/bin/env python3
"""Staging-only, explicit chapter assignment transaction.

Call only from a trusted server process after admin authentication and
independent verification of the reviewed candidate fingerprint. This module
does not accept browser-provided database credentials.
"""
import re

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$", re.I)


def validate_plan(plan, page_count):
    if not isinstance(plan, dict) or plan.get("status") != "prepared_not_applied":
        raise ValueError("Unprepared chapter plan")
    if plan.get("citation_verified") is not False or plan.get("database_written") is not False:
        raise ValueError("Untrusted approval state")
    if not isinstance(plan.get("review_fingerprint"), str) or not re.fullmatch(r"[a-f0-9]{64}", plan["review_fingerprint"]):
        raise ValueError("Missing candidate fingerprint")
    sections = plan.get("sections")
    if not isinstance(sections, list) or not sections or len(sections) > 2000:
        raise ValueError("Invalid section count")
    if type(page_count) is not int or page_count < 1:
        raise ValueError("Invalid textbook page count")
    previous = 0
    chapter_seen = False
    previous_group = 0
    for section in sections:
        if not isinstance(section, dict):
            raise ValueError("Invalid section")
        page = section.get("start_page")
        heading = section.get("heading")
        kind = section.get("kind")
        group = section.get("group")
        detector = section.get("detector")
        if type(group) is not int or group <= previous_group:
            raise ValueError("Section review groups must be strictly increasing")
        if detector not in ("text", "layout"):
            raise ValueError("Unknown chapter detector")
        if type(page) is not int or not previous < page <= page_count:
            raise ValueError("Section pages must be strictly increasing and within PDF")
        if not isinstance(heading, str) or not heading.strip() or len(heading) > 500:
            raise ValueError("Invalid heading")
        if kind not in ("Chapter", "Subsection"):
            raise ValueError("Invalid section kind")
        if kind == "Subsection" and not chapter_seen:
            raise ValueError("Subsection without parent chapter")
        if kind == "Chapter":
            chapter_seen = True
        previous_group = group
        previous = page
    return sections


def apply_plan(connection, owner_uid, textbook_id, plan, expected_fingerprint):
    """Replace sections atomically; never modify passage text or citation flags.

    expected_fingerprint must be independently computed from the current
    trusted R2 extraction, never copied from the submitted plan.
    """
    if not isinstance(owner_uid, str) or not UUID.fullmatch(owner_uid):
        raise ValueError("Invalid owner UUID")
    if not isinstance(textbook_id, str) or not UUID.fullmatch(textbook_id):
        raise ValueError("Invalid textbook UUID")
    if not isinstance(expected_fingerprint, str) or not re.fullmatch(r"[a-f0-9]{64}", expected_fingerprint):
        raise ValueError("Invalid independently verified fingerprint")
    if not isinstance(plan, dict) or plan.get("review_fingerprint") != expected_fingerprint:
        raise ValueError("Candidate fingerprint mismatch")
    with connection.transaction():
        with connection.cursor() as cur:
            cur.execute(
                """select id, page_count from source_library_staging.textbooks
                   where id=%s::uuid and owner_uid=%s::uuid and status='ready'
                   for update""", (textbook_id, owner_uid))
            row = cur.fetchone()
            if row is None:
                raise ValueError("Ready textbook not found for owner")
            sections = validate_plan(plan, row[1])
            # Clear referencing FKs before deleting old sections; transaction rolls back on failure.
            cur.execute("update source_library_staging.passages set section_id=null where textbook_id=%s::uuid", (textbook_id,))
            cur.execute("delete from source_library_staging.sections where textbook_id=%s::uuid", (textbook_id,))
            current_chapter = None
            assigned = []
            for order, section in enumerate(sections):
                parent = current_chapter if section["kind"] == "Subsection" else None
                cur.execute(
                    """insert into source_library_staging.sections
                       (textbook_id,parent_section_id,heading,section_order,start_page)
                       values (%s::uuid,%s::uuid,%s,%s,%s) returning id""",
                    (textbook_id, parent, section["heading"], order, section["start_page"]))
                sid = cur.fetchone()[0]
                if section["kind"] == "Chapter":
                    current_chapter = sid
                assigned.append((section["start_page"], sid))
            # Use the last approved boundary not after the passage's first PDF page.
            # Existing passages preceding the first chapter remain unassigned.
            cur.execute(
                """update source_library_staging.passages p
                   set section_id=(
                       select s.id from source_library_staging.sections s
                       where s.textbook_id=p.textbook_id and s.start_page<=p.page_start
                       order by s.start_page desc, s.section_order desc limit 1)
                   where p.textbook_id=%s::uuid""", (textbook_id,))
            return {"sections_applied": len(assigned), "citation_verified": False,
                    "textbook_id": textbook_id}
