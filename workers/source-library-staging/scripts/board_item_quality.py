"""Board-style item blueprint and deterministic pre-review checks.

Targets are authoring preferences, not claims of NBCRNA psychometric calibration.
Official NCE domain weights: NBCRNA content outline effective January 2024.
"""
import re

NCE_DOMAINS = {
    "basic_sciences": 20,
    "equipment_instrumentation_technology": 20,
    "general_principles_of_anesthesia": 35,
    "surgical_procedures_special_populations": 25,
}
SEE_DOMAINS = {domain: 25 for domain in NCE_DOMAINS}
BLUEPRINTS = {"NCE": NCE_DOMAINS, "SEE": SEE_DOMAINS}
REASONING_TARGETS = {
    "clinical_application_management": 40,
    "physiology_pharmacology_integration": 25,
    "interpretation_troubleshooting": 20,
    "foundations_calculations": 15,
}
DIFFICULTY_TARGETS = {"foundational": 20, "moderate": 50, "advanced": 30}
ITEM_FORMATS = ("single", "multi", "calculation", "drag_drop", "hotspot", "graphics")
EXPLANATION_SECTIONS = (
    "The Core Concept:", "Why the Correct Answer Wins:",
    "The Trap Identified:", "Distractor Breakdown:",
)
REVIEW_GATES = (
    "single_best_answer", "clinical_ambiguity", "numeric_accuracy",
    "correct_answer_source_support", "distractor_source_support",
    "counterfactual_relevance", "independent_blind_review",
)


def review_item(item, *, known_stems=()):
    """Return deterministic flags; semantic/clinical judgments remain pending."""
    errors = []
    if not isinstance(item, dict):
        return {"errors": ["Invalid item"], "pending_review": list(REVIEW_GATES), "eligible_for_approval": False}
    kind = item.get("type", "single")
    if kind not in ITEM_FORMATS:
        errors.append("Unsupported item format")
    if not isinstance(item.get("stem"), str) or not item["stem"].strip():
        errors.append("Question stem required")
    if kind in ("single", "multi"):
        options = item.get("options")
        answers = item.get("answer")
        if not isinstance(options, list) or len(options) != 4 or not all(isinstance(x, str) and x.strip() for x in options):
            errors.append("Exactly four nonempty options required")
        elif len(set(x.strip().casefold() for x in options)) != 4:
            errors.append("Duplicate options")
        if not isinstance(answers, list) or not answers or not all(type(x) is int and 0 <= x < 4 for x in answers) or len(set(answers)) != len(answers):
            errors.append("Invalid answer indexes")
        elif (kind == "single" and len(answers) != 1) or (kind == "multi" and len(answers) < 2):
            errors.append("Incorrect number of keyed answers")
    if kind in ("calculation", "drag_drop", "hotspot", "graphics"):
        errors.append("Alternative item renderer and schema not yet implemented")
    explanation = item.get("explanation", "")
    if not isinstance(explanation, str) or any(section not in explanation for section in EXPLANATION_SECTIONS):
        errors.append("Required explanation sections missing")
    if not item.get("sourceExcerpt"):
        errors.append("Source statement missing")
    if item.get("sourceExcerptMatch") != "exact":
        errors.append("Source excerpt not matched to indexed passage")
    if item.get("evidenceVerificationStatus") != "verified" or not item.get("citationVerified"):
        errors.append("Source evidence not independently verified")
    if not item.get("nceDomain") in NCE_DOMAINS:
        errors.append("NCE domain unassigned")
    if not item.get("reasoningCategory") in REASONING_TARGETS:
        errors.append("Reasoning category unassigned")
    if not item.get("difficultyTier") in DIFFICULTY_TARGETS:
        errors.append("Difficulty tier unassigned")
    norm = lambda x: re.sub(r"\W+", " ", str(x).casefold()).strip()
    if norm(item.get("stem", "")) in {norm(x) for x in known_stems}:
        errors.append("Duplicate stem")
    return {"errors": errors, "pending_review": list(REVIEW_GATES),
            "eligible_for_approval": False}


def blueprint_counts(total, weights):
    """Largest-remainder allocation preserves the exact requested count."""
    if type(total) is not int or total < 0 or sum(weights.values()) != 100:
        raise ValueError("Invalid blueprint")
    raw = {k: total * v / 100 for k, v in weights.items()}
    counts = {k: int(v) for k, v in raw.items()}
    remainder = total - sum(counts.values())
    for key in sorted(weights, key=lambda k: (-(raw[k] - counts[k]), list(weights).index(k)))[:remainder]:
        counts[key] += 1
    return counts
