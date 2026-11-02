"""Strict v2.0 generation contract, separate from legacy question generation.

Section 18 requires separate concept-card, item-draft and rationale calls.
This module builds requests only: no network, credentials, database or paid AI calls.
"""
from item_standard_v2 import check as schema_check

RULES_VERSION = "2.0"
FORMATS = ("MC", "MS", "SA", "DD", "HS")
STEPS = ("concept_card", "item_draft", "rationale")


def build_step(step, *, mode, domain, section, objective, evidence, format=None,
               concept_card=None, draft=None):
    if step not in STEPS:
        raise ValueError("Unknown generation step")
    if mode not in ("NCE", "SEE") or domain not in ("I", "II", "III", "IV"):
        raise ValueError("Invalid exam mode/domain")
    if not isinstance(section, str) or not section.strip() or not isinstance(objective, str) or not objective.strip():
        raise ValueError("Section and objective required")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Indexed evidence required")
    for passage in evidence:
        if not isinstance(passage, dict) or not all(passage.get(k) for k in ("passage_id", "textbook_id", "excerpt")):
            raise ValueError("Each source requires passage ID, textbook ID and excerpt")
    if step in ("item_draft", "rationale") and format not in FORMATS:
        raise ValueError("One of five v2.0 formats required")
    if step in ("item_draft", "rationale") and not isinstance(concept_card, dict):
        raise ValueError("Concept card required before drafting")
    if step == "rationale" and not isinstance(draft, dict):
        raise ValueError("Draft required before rationale")
    instructions = {
        "concept_card": "Produce a concept card with objective, mechanism, relevance, misconception, counterfactual and evidence_ids. Ground all clinical claims in the supplied passages.",
        "item_draft": "Create exactly one original NBCRNA-style item in the requested format. Use clinical application or analysis when appropriate. Do not invent citations or unsupported facts. MC: four options, one correct. MS: four to six options, select exactly two or three. SA: numeric with unit, rounding, tolerance and worked solution. DD: four-to-four one-to-one match. HS: licensed figure and correct plus two adjacent near-miss regions. Do not use all/none above, true/false, fill-in or select-all-that-apply.",
        "rationale": "Write core_concept, why_key_wins, trap and distractor_breakdown. Verify each distractor is false using evidence; do not invent citations. Preserve draft answer and source IDs. Leave uncertain facts flagged for human review.",
    }
    return {"rules_version": RULES_VERSION, "step": step,
            "mode": mode, "domain": domain, "section": section, "objective": objective,
            "format": format, "evidence": evidence, "concept_card": concept_card,
            "draft": draft, "instructions": instructions[step],
            "required_output": ("concept_card" if step == "concept_card"
                                else "draft" if step == "item_draft" else "rationale"),
            "human_review_required": True, "auto_publish": False}


def validate_complete_item(item):
    if not isinstance(item, dict) or item.get("rules_version") != RULES_VERSION:
        return [{"rule_id": "R-15", "message": "Expected complete v2.0 item"}]
    return schema_check(item)
