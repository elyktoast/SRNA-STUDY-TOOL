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
        "concept_card": "Return one FLAT JSON object, not a nested concept_card wrapper. Required keys: objective (string EXACTLY matching the input objective code), mechanism (nonempty string), relevance (nonempty string), misconception (nonempty string), counterfactual (nonempty string), evidence_ids (nonempty array of UNIQUE passage_id strings copied verbatim from supplied evidence). Do not use textbook_id, page number, citation label, or invented IDs in evidence_ids. Ground all clinical claims in the supplied passages. Do not add markdown.",
        "item_draft": "Return exactly one FLAT JSON object (no draft/item wrapper). Include format EXACTLY equal to the requested two-letter format (MC, MS, SA, DD, HS), and a nonempty string stem. Use clinical application or analysis when appropriate; do not invent citations or unsupported facts. For MC: options must be an array of exactly four objects with id A, B, C, D, nonempty text and error_pattern; key must be an array containing exactly one correct option ID; select_count must be null. For MS: four to six such sequential options, key an array of exactly two or three correct IDs, select_count equal to that number, and stem must contain (Select 2.) or (Select 3.). For SA: numeric sa.answer, sa.tolerance, sa.unit, sa.rounding, sa.worked_solution, with no choices. For DD: dd.left and dd.right arrays of four each, and dd.pairs one-to-one. For HS: only a genuinely licensed figure with license, correct_region and two near_miss_regions; never invent a license. Include reasoning_level (recall, application or analysis), population (adult, pediatric, obstetric, geriatric, obese, SUD, immune or null), crisis_scenario (boolean), evidence (array of source objects with textbook_id, passage_id and pdf_page drawn only from supplied passages), and fields model, distractor_evidence, numbers_verified_against_page_image (false unless independently verified), enemy_ids, self_check, audit and stats. For unused format-specific fields sa, dd, and hs use explicit null values; include ALL THREE keys even for MC/MS. Include audit as an array, self_check as an object, and stats as an object; empty containers are allowed only when not yet evaluated and must never imply approval. For each evidence citation include excerpt copied verbatim as a nonempty substring of the supplied passage excerpt, along with its exact textbook_id, passage_id, and pdf_page_start as pdf_page. For MC/MS, distractor_evidence MUST be an object with exactly one entry per option ID; each entry has verdict (supports_key for the keyed option, refutes_distractor for other options), passage_ids (nonempty array of supplied passage IDs), and explanation (nonempty evidence-based text). If the supplied passage cannot justify a choice, do not fabricate an evidence link; explicitly flag uncertainty for human review. Never claim human approval or verified page images. No all/none above, true/false, fill-in or select-all-that-apply.",
        "rationale": "Write core_concept, why_key_wins, trap and distractor_breakdown. Verify each distractor is false using evidence; do not invent citations. Preserve draft answer and source IDs. Leave uncertain facts flagged for human review.",
    }
    # Keep the full evidence in trusted validation; send only fields the model
    # needs for grounding and source attribution. Do not truncate excerpts.
    compact_evidence = [{key: passage[key] for key in
        ("passage_id", "textbook_id", "excerpt", "pdf_page_start", "pdf_page_end")
        if key in passage} for passage in evidence]
    return {"rules_version": RULES_VERSION, "step": step,
            "mode": mode, "domain": domain, "section": section, "objective": objective,
            "format": format, "evidence": compact_evidence, "concept_card": concept_card,
            "draft": draft, "instructions": instructions[step],
            "required_output": ("concept_card" if step == "concept_card"
                                else "draft" if step == "item_draft" else "rationale"),
            "human_review_required": True, "auto_publish": False}


def validate_complete_item(item):
    if not isinstance(item, dict) or item.get("rules_version") != RULES_VERSION:
        return [{"rule_id": "R-15", "message": "Expected complete v2.0 item"}]
    return schema_check(item)
