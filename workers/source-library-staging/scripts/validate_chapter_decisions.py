#!/usr/bin/env python3
"""Validate offline chapter review decisions. Does not approve or write sections."""
import json

CHOICES = {"Needs review", "Chapter", "Subsection", "Reject"}

def validate_decisions(payload, groups):
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Unsupported review format")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list) or len(decisions) != len(groups):
        raise ValueError("Every review group must have one decision")
    checked = []
    for expected, entry in enumerate(decisions, 1):
        if not isinstance(entry, dict) or type(entry.get("group")) is not int or entry["group"] != expected:
            raise ValueError("Group order or identity mismatch")
        choice = entry.get("decision")
        note = entry.get("notes")
        if choice not in CHOICES or not isinstance(note, str) or len(note) > 2000:
            raise ValueError("Invalid review decision")
        checked.append({"group": expected, "decision": choice, "notes": note,
                        "page_range": [groups[expected-1]["first_page"],
                                       groups[expected-1]["last_page"]]})
    return {"status": "validated_unapproved", "decisions": checked,
            "database_written": False, "sections_approved": 0}

def validate_file(path, groups):
    with open(path, encoding="utf-8") as stream:
        return validate_decisions(json.load(stream), groups)
