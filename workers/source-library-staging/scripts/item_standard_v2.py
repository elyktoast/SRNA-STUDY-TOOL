"""NCE/SEE v2.0 Section 15 authoring contract. New items only.

Legacy ~7000 questions are not migrated or mutated. A valid schema never
implies clinical accuracy or approval (R-12.10, R-13.1).
"""
import math
import re

FORMATS = {"MC", "MS", "SA", "DD", "HS"}
STATES = {"draft", "needs_source_review", "needs_clinical_review",
          "needs_editorial_review", "verified_evidence", "approved",
          "published", "retired"}
DOMAINS = {"I", "II", "III", "IV"}
LEVELS = {"recall", "application", "analysis"}
POPULATIONS = {"adult", "pediatric", "obstetric", "geriatric", "obese", "SUD", "immune", None}
REQUIRED = ("item_id", "rules_version", "model", "mode", "domain", "section",
            "objective", "format", "reasoning_level", "population", "crisis_scenario",
            "concept_card", "stem", "select_count", "options", "sa", "dd", "hs",
            "key", "rationale", "evidence", "distractor_evidence",
            "numbers_verified_against_page_image", "enemy_ids", "self_check",
            "status", "audit", "stats")
CARD_FIELDS = ("objective", "mechanism", "relevance", "misconception",
               "counterfactual", "evidence_ids")
RATIONALE_FIELDS = ("core_concept", "why_key_wins", "trap", "distractor_breakdown")


def check(item):
    """Return stable rule-ID diagnostics. Fail closed; no automatic approval."""
    issues = []
    def fail(rule, message):
        issues.append({"rule_id": rule, "message": message})
    if not isinstance(item, dict):
        return [{"rule_id": "R-0.1", "message": "Item must be an object"}]
    for field in REQUIRED:
        if field not in item:
            fail("R-15", "Missing field: " + field)
    if item.get("rules_version") != "2.0":
        fail("R-14.6", "rules_version must be 2.0")
    if item.get("mode") not in ("NCE", "SEE") or item.get("domain") not in DOMAINS:
        fail("R-1.1", "Invalid mode or domain")
    if not isinstance(item.get("section"), str) or not re.fullmatch("[A-Z]", item["section"]):
        fail("R-1.2", "Invalid section")
    if not isinstance(item.get("objective"), str) or not re.fullmatch(r"(I|II|III|IV)\.[A-Z]\.\d+(?:\.\d+)*", item["objective"]):
        fail("R-1.3", "Objective must be a numbered blueprint path")
    elif item["objective"].split(".")[:2] != [item.get("domain"), item.get("section")]:
        fail("R-1.3", "Objective and domain/section disagree")
    if item.get("reasoning_level") not in LEVELS or item.get("population") not in POPULATIONS or type(item.get("crisis_scenario")) is not bool:
        fail("R-1.3", "Invalid reasoning, population, or crisis tags")
    if not isinstance(item.get("stem"), str) or not item["stem"].strip():
        fail("R-4.1", "Nonempty stem required")
    card = item.get("concept_card")
    if not isinstance(card, dict) or any(k not in card for k in CARD_FIELDS) or not isinstance(card.get("evidence_ids"), list):
        fail("R-3.3", "Incomplete concept card")
    rationale = item.get("rationale")
    if not isinstance(rationale, dict) or any(k not in rationale for k in RATIONALE_FIELDS) or not isinstance(rationale.get("distractor_breakdown"), dict):
        fail("R-9", "Four-part rationale required")
    fmt = item.get("format")
    if fmt not in FORMATS:
        fail("R-7.6", "Unsupported or banned format")
    opts, key = item.get("options"), item.get("key")
    if fmt in ("MC", "MS"):
        count = len(opts) if isinstance(opts, list) else 0
        if (fmt == "MC" and count != 4) or (fmt == "MS" and count not in (4, 5, 6)):
            fail("R-7.1.1" if fmt == "MC" else "R-7.2.2", "Invalid option count")
        ids = [o.get("id") for o in opts if isinstance(o, dict)] if isinstance(opts, list) else []
        if ids != list("ABCDEF")[:count] or any(not isinstance(o.get("text"), str) or not o["text"].strip() or "error_pattern" not in o for o in opts if isinstance(o, dict)):
            fail("R-15", "Options must be labeled sequentially and have text and error pattern")
        if not isinstance(key, list) or not key or len(set(key)) != len(key) or any(k not in ids for k in key):
            fail("R-5.1", "Invalid keyed choices")
        elif (fmt == "MC" and len(key) != 1) or (fmt == "MS" and len(key) not in (2, 3)):
            fail("R-5.1", "Invalid number of correct choices")
        if fmt == "MS":
            n = item.get("select_count")
            if n not in (2, 3) or not isinstance(key, list) or len(key) != n or f"(Select {n}.)" not in item.get("stem", ""):
                fail("R-7.2.1", "Explicit select count and stem wording required")
        elif item.get("select_count") is not None:
            fail("R-15", "MC select_count must be null")
        texts = [o.get("text", "").strip().casefold() for o in opts if isinstance(o, dict)]
        if len(set(texts)) != len(texts):
            fail("R-6.5", "Duplicate options")
        if any("all of the above" in t or "none of the above" in t for t in texts):
            fail("R-6.11", "Combination options prohibited")
    elif fmt == "SA":
        sa = item.get("sa")
        if not isinstance(sa, dict) or type(sa.get("answer")) not in (int, float) or not math.isfinite(sa["answer"]) or type(sa.get("tolerance")) not in (int, float) or not 0 <= sa["tolerance"] < float("inf") or not all(isinstance(sa.get(k), str) and sa[k].strip() for k in ("unit", "rounding", "worked_solution")):
            fail("R-7.3", "Complete finite numeric answer, tolerance, units and solution required")
        if opts not in ([], None):
            fail("R-7.3", "Numeric entry cannot have choices")
    elif fmt == "DD":
        dd = item.get("dd")
        if not isinstance(dd, dict) or not all(isinstance(dd.get(k), list) and len(dd[k]) == 4 for k in ("left", "right")) or not isinstance(dd.get("pairs"), dict) or len(dd["pairs"]) != 4 or len(set(dd["pairs"].values())) != 4:
            fail("R-7.4.1", "Four unique one-to-one matches required")
    elif fmt == "HS":
        hs = item.get("hs")
        if not isinstance(hs, dict) or any(not hs.get(k) for k in ("figure", "license", "correct_region")) or not isinstance(hs.get("near_miss_regions"), list) or len(hs["near_miss_regions"]) != 2:
            fail("R-7.5", "Licensed figure and two near-miss regions required")
    if item.get("status") not in STATES:
        fail("R-13", "Invalid review state")
    if not isinstance(item.get("evidence"), list) or not item["evidence"]:
        fail("R-2.5", "Source evidence required")
    elif any(not isinstance(e, dict) or any(not e.get(k) for k in ("textbook_id", "passage_id", "pdf_page")) for e in item["evidence"]):
        fail("R-2.5", "Evidence must resolve textbook, passage and PDF page")
    if type(item.get("numbers_verified_against_page_image")) is not bool:
        fail("R-8.5", "Numeric verification state required")
    if not isinstance(item.get("audit"), list) or not isinstance(item.get("self_check"), dict) or not isinstance(item.get("stats"), dict):
        fail("R-15", "Audit, self-check and stats required")
    return issues
