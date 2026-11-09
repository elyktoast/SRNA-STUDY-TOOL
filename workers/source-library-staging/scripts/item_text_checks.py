"""Deterministic v2.0 editorial checks; flags are not clinical judgments."""
import re

ABSOLUTES = re.compile(r"\b(always|never|only|sole|all|none|completely)\b", re.I)
WORDS = re.compile(r"[A-Za-z0-9]+")


def check(item, source_texts=()):
    issues = []
    if item.get("format") not in ("MC", "MS"):
        return issues
    options = item.get("options", [])
    if not isinstance(options, list) or not all(isinstance(o, dict) and isinstance(o.get("text"), str) for o in options):
        return [{"rule_id": "R-15", "message": "Options malformed"}]
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
    candidates = [item.get("stem", "")] + [o["text"] for o in options]
    sources = [WORDS.findall(source.casefold()) for source in source_texts if isinstance(source, str)]
    for candidate in candidates:
        tokens = WORDS.findall(candidate.casefold())
        if any(tuple(tokens[i:i+8]) in {tuple(src[j:j+8]) for j in range(len(src)-7)}
               for i in range(max(0, len(tokens)-7)) for src in sources):
            issues.append({"rule_id": "R-2.8", "message": "Eight-word source overlap detected"})
            break
    return issues
