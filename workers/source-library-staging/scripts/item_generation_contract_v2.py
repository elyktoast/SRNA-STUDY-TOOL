"""Strict v2.0 generation contract, separate from legacy question generation.

Section 18 requires separate concept-card, item-draft and rationale calls.
This module builds requests only: no network, credentials, database or paid AI calls.
"""
from item_standard_v2 import check as schema_check

RULES_VERSION = "2.0"
FORMATS = ("MC", "MS", "SA", "DD", "HS")
STEPS = ("concept_card", "item_draft", "rationale")


def build_step(step, *, mode, domain, section, objective, evidence, format=None,
               concept_card=None, draft=None, topic=None):
    if step not in STEPS:
        raise ValueError("Unknown generation step")
    if topic is not None and (not isinstance(topic, str) or not topic.strip() or len(topic) > 500):
        raise ValueError("Invalid selected topic")
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
        "concept_card": "Return one FLAT JSON object, not a nested concept_card wrapper. Required keys: objective (string EXACTLY matching the input objective code), mechanism (nonempty string), relevance (nonempty string), misconception (nonempty string), counterfactual (nonempty string), evidence_ids (nonempty array of UNIQUE passage_id strings copied verbatim from supplied evidence). Do not use textbook_id, page number, citation label, or invented IDs in evidence_ids. Ground all clinical claims in the supplied passages. If the excerpt only classifies agents, mechanism must describe that classification; do not add receptor physiology from memory. In multi-column text, only explicit table entries establish category membership; nearby treatment prose does not join a category automatically. Present a misconception as a potential incorrect inference without inventing its prevalence. Use a narrow counterfactual supported by that classification. Relevance must state only the direct clinical importance of the supplied mechanism; do not invent inventory, stocking, regulatory or workflow requirements. A source describing where rescue treatment must be stocked does not prohibit stocking triggering drugs. Do not add markdown.",
        "item_draft": "Return exactly one FLAT JSON object (no draft/item wrapper). Include format EXACTLY equal to the requested two-letter format (MC, MS, SA, DD, HS), and a nonempty string stem. Use clinical application or analysis when appropriate; do not invent citations or unsupported facts. Assess the selected mechanism directly; do not drift to related interventions. For MC: options must be an array of exactly four objects with id A, B, C, D, nonempty text and error_pattern; key must be an array containing exactly one correct option ID; select_count must be null. For MS: four to six such sequential options, key an array of exactly two or three correct IDs, select_count equal to that number, and stem must contain (Select 2.) or (Select 3.). For SA: numeric sa.answer, sa.tolerance, sa.unit, sa.rounding, sa.worked_solution, with no choices. For DD: dd.left and dd.right arrays of four each, and dd.pairs one-to-one. For HS: only a genuinely licensed figure with license, correct_region and two near_miss_regions; never invent a license. Include reasoning_level (recall, application or analysis), population (adult, pediatric, obstetric, geriatric, obese, SUD, immune or null), crisis_scenario (boolean), evidence (array of source objects with textbook_id, passage_id and pdf_page drawn only from supplied passages), and fields model, distractor_evidence, TOP-LEVEL numbers_verified_against_page_image (always false in this text-only generation step), enemy_ids, self_check, audit and stats. For unused format-specific fields sa, dd, and hs use explicit null values; include ALL THREE keys even for MC/MS. Include audit as an array, self_check as an object, and stats as an object; empty containers are allowed only when not yet evaluated and must never imply approval. For each evidence citation, return an object with exactly textbook_id, passage_id, and pdf_page copied from the supplied source (use pdf_page_start as pdf_page). Omit excerpt: the trusted server attaches the exact indexed text after verifying all three source identifiers. If the passage lacks pdf_page_start, flag it for human review; do not guess a pdf_page. Return an array of OBJECTS ONLY, with no empty strings, separators, null entries, ellipses or reconstructed quotations. Include a citation for every passage ID used in distractor_evidence. A source reference is not proof that it supports a claim; each option explanation must still identify affirmative support or contradiction in that source. For MC/MS, distractor_evidence MUST be an object with exactly one entry per option ID; each entry has verdict (supports_key for the keyed option, refutes_distractor for other options), passage_ids (nonempty array of supplied passage IDs), and explanation (nonempty evidence-based text). Build the distractor_evidence map in the same item_draft response, not a later rationale call. Check that its keys exactly match the option IDs, that each passage ID exists in the supplied evidence, and that each explanation identifies affirmative support or contradiction from the source rather than silence. For a negatively worded NOT/EXCEPT stem, supports_key marks the option answering the negative question; the other verdicts must still be grounded in the passage. If the supplied passage cannot justify a choice, do not fabricate an evidence link; explicitly flag uncertainty for human review. Follow NCE/SEE Item Generation Standard v2.0 as governing authority: R-2.1 and R-2.4 require positive source evidence for the key AND evidence showing every distractor false; absence from a passage is not disproof. R-2.8 prohibits copying eight or more consecutive source words into the stem or options. R-4.3 requires each stem detail to matter; R-4.8 discourages NOT/EXCEPT. R-5.3 requires a meaningful counterfactual. R-6.1 through R-6.3 require plausible single-flaw distractors tagged by error pattern; do not use Correct or Incorrect as an error_pattern. R-6.8 requires parallel options of similar length, with the key no more than about 15 percent longer than the next-longest option. Keep options to about 6–14 words when possible, put shared context in the stem, and compare option word counts before returning the draft. R-6.9 prohibits rationale in options. Before selecting the key, perform an adversarial option-by-option test: assume EACH option could be correct, identify the clinical assumptions under which it would be true, and compare those assumptions against the exact stem. Reject or rewrite any distractor that could also satisfy the stem, including synonymous mechanisms, overlapping causes, and answers that become true when unspecified conditions are assumed. Each distractor must be false under the stated scenario, not merely less preferred. Never dismiss another true contributor as secondary or partial truth unless the supplied source explicitly establishes that hierarchy. When the source gives combined mechanisms, ask for the combination and make every option a parallel combination of the SAME TWO VARIABLES, varying only their direction or state instead of introducing other causes. The source must contradict at least one component of every incorrect combination. Do not invent a primary reason. For MS, independently verify the precise number of correct options and reject an ambiguous extra true option. When a source only supports a general mechanism but cannot resolve the scenario-specific distinction, flag uncertainty instead of forcing a unique key. R-12.9 requires duplicate concept screening. If evidence is insufficient, do not invent support or treat silence as refutation; flag for human review. Never claim human approval or verified page images. No all/none above, true/false, fill-in or select-all-that-apply.",
        "rationale": "Return exactly one FLAT JSON object with four keys: core_concept (string), why_key_wins (string), trap (string), and distractor_breakdown (object keyed by EVERY option ID, including the keyed answer(s), with string explanations). Do not wrap the object under rationale or repeat the draft, source excerpts, or evidence objects. Use one or two concise sentences per field and per option explanation. For each option, explicitly state the source-supported mechanism or classification (do not invent a mechanism when only classification is supplied), why it is correct or incorrect IN THE STEM CONTEXT, and what the supplied textbook evidence affirmatively establishes. Challenge each distractor as though it might be another correct answer; if any distractor remains defensible, identify the ambiguity for human review rather than inventing a disproof. Do not use absence from a passage as disproof. Do not invent citations. Preserve draft answer and source IDs. Leave uncertain facts flagged for human review.",
    }
    # Keep the full evidence in trusted validation; send only fields the model
    # needs for grounding and source attribution. Do not truncate excerpts.
    compact_evidence = [{key: passage[key] for key in
        ("passage_id", "textbook_id", "excerpt", "pdf_page_start", "pdf_page_end")
        if key in passage} for passage in evidence]
    return {"rules_version": RULES_VERSION, "step": step,
            **({"topic": topic} if topic is not None else {}),
            "mode": mode, "domain": domain, "section": section, "objective": objective,
            "format": format, "evidence": compact_evidence, "concept_card": concept_card,
            "draft": draft, "instructions": ("Focus on the selected topic, using only the supplied evidence for clinical claims. " if topic is not None else "") + instructions[step],
            "required_output": ("concept_card" if step == "concept_card"
                                else "draft" if step == "item_draft" else "rationale"),
            "human_review_required": True, "auto_publish": False}


def validate_complete_item(item):
    if not isinstance(item, dict) or item.get("rules_version") != RULES_VERSION:
        return [{"rule_id": "R-15", "message": "Expected complete v2.0 item"}]
    return schema_check(item)
