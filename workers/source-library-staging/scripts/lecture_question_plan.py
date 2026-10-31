"""Lecture-first generation plan; textbook passages remain authority for citations.

No model calls, file writes, or changes to the existing question bank.
"""
import re

def normalize_topics(lecture_topics):
    if not isinstance(lecture_topics, list) or not lecture_topics:
        raise ValueError("Lecture concepts required")
    result = []
    seen = set()
    for topic in lecture_topics:
        if not isinstance(topic, dict):
            raise ValueError("Lecture concepts must be objects")
        title = topic.get("title")
        if not isinstance(title, str) or not 2 <= len(title.strip()) <= 180:
            raise ValueError("Invalid lecture concept title")
        key = re.sub(r"\s+", " ", title.strip().casefold())
        if key in seen:
            continue
        seen.add(key)
        result.append({"title": title.strip(), "lecture_locator": topic.get("lecture_locator"),
                       "objective": topic.get("objective"),
                       "importance": topic.get("importance", "standard")})
    if len(result) > 100:
        raise ValueError("Too many lecture concepts")
    return result

def plan(lecture_topics, textbook_evidence_by_topic, *, count=20):
    if type(count) is not int or not 1 <= count <= 100:
        raise ValueError("Question count must be 1..100")
    topics = normalize_topics(lecture_topics)
    if not isinstance(textbook_evidence_by_topic, dict):
        raise ValueError("Textbook evidence map required")
    eligible = []
    missing = []
    for topic in topics:
        evidence = textbook_evidence_by_topic.get(topic["title"], [])
        if isinstance(evidence, list) and evidence and all(
            isinstance(p, dict) and p.get("passage_id") and p.get("textbook_id")
            and p.get("excerpt") for p in evidence
        ):
            eligible.append({**topic, "evidence": evidence})
        else:
            missing.append({**topic, "reason": "No indexed textbook passage verified"})
    allocations = {t["title"]: 0 for t in eligible}
    for index in range(count):
        if not eligible:
            break
        allocations[eligible[index % len(eligible)]["title"]] += 1
    return {"requested": count, "planned": sum(allocations.values()),
            "topics": [{**t, "question_count": allocations[t["title"]]} for t in eligible],
            "missing_textbook_support": missing,
            "coverage": {"lecture_concepts": len(topics), "grounded_concepts": len(eligible),
                         "uncovered_concepts": len(missing)},
            "auto_approved": False, "database_writes": False}
