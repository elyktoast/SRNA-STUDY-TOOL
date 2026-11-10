"""Deterministic v2.0 editorial checks; flags are not clinical judgments."""
import re

ABSOLUTES = re.compile(r"\b(always|never|only|sole|all|none|completely)\b", re.I)
WORDS = re.compile(r"[A-Za-z0-9]+")


def check(item, source_texts=()):
    from item_board_quality_v2 import obsolete_issues
    issues = obsolete_issues(item)
    if item.get("format") not in ("MC", "MS"):
        return issues
    options = item.get("options", [])
    if not isinstance(options, list) or not all(isinstance(o, dict) and isinstance(o.get("text"), str) for o in options):
        return [{"rule_id": "R-15", "message": "Options malformed"}]
    if re.search(r"\b(?:described|stated|mentioned|shown)\s+in\s+(?:the\s+)?(?:source|passage|excerpt|textbook)\b|\baccording to (?:the )?(?:source|passage|excerpt|textbook)\b",
                 str(item.get("stem", "")), re.I):
        issues.append({"rule_id":"R-4.2", "field":"stem", "message":"Question must stand alone without referring the learner to an unspecified source passage"})
    import json
    authored = json.dumps([item.get("stem", ""), options, item.get("concept_card", {}), item.get("rationale", {})])
    if item.get("numbers_verified_against_page_image") is not True and re.search(
            r"\b\d+(?:\.\d+)?\s*(?:%|(?:mcg|mg|mL|IU|units?)(?:/kg|/mL)?\b)", authored, re.I):
        issues.append({"rule_id":"R-8.5", "field":"content", "message":"Dose, concentration or percentage requires original-page-image verification; text-only generation cannot certify it"})
    if item.get("numbers_verified_against_page_image") is not True and re.search(
            r"\b(?:divided by|multiplied by)\b|\b(?:calculate\w*|formula|equation)\b.{0,180}[=÷×]", authored, re.I):
        issues.append({"rule_id":"R-8.5", "field":"content", "message":"An authored equation requires original-page-image verification, including equations expressed in words"})
    raw_key = item.get("key")
    key = set(raw_key) if isinstance(raw_key, list) and all(isinstance(k, str) for k in raw_key) else set()
    lengths = [(o["id"], len(o["text"].split())) for o in options if isinstance(o.get("id"), str)]
    correct = [length for oid, length in lengths if oid in key]
    wrong = [length for oid, length in lengths if oid not in key]
    longer = len(key) == 1 and correct and wrong and max(wrong) > 0 and correct[0] > max(wrong) * 1.15
    if longer and all(length <= 3 for _, length in lengths):
        # Word boundaries in short names are not an explanatory length cue.
        # Require an actual visible-length difference as well; prose retains
        # the unchanged 15% word-count check below.
        chars = [(o["id"], len(" ".join(o["text"].split()))) for o in options if isinstance(o.get("id"), str)]
        key_chars = [n for oid, n in chars if oid in key]
        wrong_chars = [n for oid, n in chars if oid not in key]
        longer = key_chars[0] > max(wrong_chars) * 1.15
    if longer:
        issues.append({"rule_id": "R-6.8", "message": "Key is more than 15% longer than longest distractor"})
    if any(ABSOLUTES.search(o["text"]) for o in options if o.get("id") not in key):
        issues.append({"rule_id": "R-6.10", "message": "Absolute wording in distractor requires review"})
    if any(re.search(r"\b(?:all|none) of the above\b", o["text"], re.I) for o in options):
        issues.append({"rule_id": "R-6.11", "message": "All/none of the above prohibited"})
    if any(re.match(r"\s*(?:apply(?:ing)?|administer(?:ing)?|giv(?:e|ing)|us(?:e|ing)|provid(?:e|ing))\b", o["text"], re.I)
           and re.search(r"\b(?:because|thereby|so that|in order to|to (?:increase|decrease|prevent|reduce|improve|maximize|maintain|restore))\b", o["text"], re.I)
           for o in options):
        issues.append({"rule_id":"R-6.9", "field":"options", "message":"An intervention choice contains its own explanatory rationale"})
    candidates = [item.get("stem", "")] + [o["text"] for o in options]
    sources = [WORDS.findall(source.casefold()) for source in source_texts if isinstance(source, str)]
    for candidate in candidates:
        tokens = WORDS.findall(candidate.casefold())
        if any(tuple(tokens[i:i+8]) in {tuple(src[j:j+8]) for j in range(len(src)-7)}
               for i in range(max(0, len(tokens)-7)) for src in sources):
            issues.append({"rule_id": "R-2.8", "message": "Eight-word source overlap detected"})
            break
    return issues
