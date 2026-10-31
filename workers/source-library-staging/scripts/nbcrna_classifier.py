"""Conservative rule-based candidate classification for indexed textbook passages.

A suggested NBCRNA classification is never considered verified. Ambiguous matches
abstain instead of guessing. The classifier does not access or mutate the database.
"""
import re
from nbcrna_taxonomy import SECTIONS, OBJECTIVES

# High-specificity synonyms for a useful first pass. These are *candidate* labels.
PHRASES = {
 ("basic_sciences", "C", "Local anesthetics"): ("local anesthetic pharmacology", "lidocaine toxicity", "bupivacaine toxicity"),
 ("basic_sciences", "C", "Inhalation anesthetics"): ("minimum alveolar concentration", "volatile anesthetic uptake"),
 ("basic_sciences", "C", "Depolarizing and nondepolarizing neuromuscular relaxants and antagonists"): ("neuromuscular blocking agent", "succinylcholine", "rocuronium", "sugammadex"),
 ("equipment_instrumentation_technology", "A", "Vaporizers"): ("variable bypass vaporizer", "desflurane vaporizer"),
 ("equipment_instrumentation_technology", "A", "Carbon dioxide absorbents"): ("carbon dioxide absorbent", "soda lime"),
 ("equipment_instrumentation_technology", "C", "Respiratory"): ("capnography waveform", "pulse oximeter"),
 ("general_principles_of_anesthesia", "H", "Difficult airway management"): ("difficult airway algorithm", "cannot intubate cannot oxygenate"),
 ("general_principles_of_anesthesia", "I", "Management of complications"): ("local anesthetic systemic toxicity",),
 ("general_principles_of_anesthesia", "E", "Massive transfusion protocol"): ("massive transfusion protocol",),
 ("surgical_procedures_special_populations", "A", "Cardiac anesthesia"): ("cardiopulmonary bypass", "transcatheter aortic valve replacement"),
 ("surgical_procedures_special_populations", "B", "Obstetrics"): ("obstetric anesthesia", "postpartum hemorrhage"),
 ("surgical_procedures_special_populations", "B", "Pediatrics"): ("pediatric anesthesia", "neonatal anesthesia"),
}


def _has_phrase(text, phrase):
    return re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text) is not None


def suggest(text, *, min_score=1):
    if not isinstance(text, str) or not text.strip():
        return {"status": "unclassified", "candidates": [], "requires_review": True}
    normalized = re.sub(r"\s+", " ", text.casefold())
    scores = []
    for (domain, section, objective), phrases in PHRASES.items():
        hits = [phrase for phrase in phrases if _has_phrase(normalized, phrase)]
        if len(hits) >= min_score:
            scores.append({"domain": domain, "section": section, "objective": objective,
                           "score": len(hits), "matched_terms": hits})
    scores.sort(key=lambda x: (-x["score"], x["domain"], x["section"], x["objective"]))
    if not scores:
        return {"status": "unclassified", "candidates": [], "requires_review": True}
    best = scores[0]["score"]
    tied = sum(candidate["score"] == best for candidate in scores)
    return {"status": "suggested" if tied == 1 else "ambiguous",
            "candidates": scores[:5], "requires_review": True}


def classify_passages(passages):
    """Accept retrieved rows and return only passage IDs and suggested taxonomy."""
    results = []
    for row in passages:
        result = suggest(row.get("excerpt", ""))
        results.append({"passage_id": row["passage_id"], **result})
    return results
