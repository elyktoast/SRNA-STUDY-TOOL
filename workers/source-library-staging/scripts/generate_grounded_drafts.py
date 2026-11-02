#!/usr/bin/env python3
"""Private backend orchestration: indexed evidence -> existing generator -> review drafts.

The caller supplies a short-lived, authenticated staging JWT. Never log tokens,
source passages, or generated medical content. No questions are auto-approved.
"""
import json
import re
import urllib.error
import urllib.request

from prepare_grounded_generation import prepare
from board_item_quality import review_item
from nbcrna_taxonomy import validate_classification


def generate_drafts(conn, owner_uid, topic, *, endpoint, jwt, apikey,
                    textbook_id=None, count=5, transport=None):
    if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
        raise ValueError("HTTPS generator endpoint required")
    from urllib.parse import urlsplit
    parsed = urlsplit(endpoint)
    if parsed.username or parsed.password or parsed.query or parsed.fragment or not parsed.hostname or parsed.hostname in ("localhost", "127.0.0.1"):
        raise ValueError("Invalid generator endpoint")
    if parsed.path != "/functions/v1/generate-questions":
        raise ValueError("Unexpected generator endpoint")
    if not jwt or not apikey:
        raise ValueError("Authenticated generator credentials required")
    payload = prepare(conn, owner_uid, topic, textbook_id=textbook_id, count=count)
    if transport is None:
        def transport(url, body, headers):
            req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                         headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=90) as response:
                if response.status != 200:
                    raise ValueError("Generator returned non-success status")
                return json.loads(response.read(2_000_001))
    raw = transport(endpoint, {k: payload[k] for k in ("material", "sourceName", "citation", "count")},
                    {"Authorization": "Bearer " + jwt, "apikey": apikey,
                     "Content-Type": "application/json"})
    questions = raw.get("questions") if isinstance(raw, dict) else None
    if not isinstance(questions, list) or not questions or len(questions) > count:
        raise ValueError("Invalid generated question count")
    source_blocks = re.findall(r"\[SOURCE \d+ \| passage_id=([^ |]+) \| textbook_id=[^\]]+\]\n(.*?)(?=\n\n\[SOURCE |\Z)", payload["material"], flags=re.S)
    if not source_blocks:
        raise ValueError("Indexed source passage references missing")
    allowed_passages = {pid: text for pid, text in source_blocks}
    drafts = []
    for question in questions:
        if not isinstance(question, dict):
            raise ValueError("Invalid generated question")
        choices = question.get("options")
        answers = question.get("answer")
        if (not isinstance(question.get("stem"), str) or
                not isinstance(choices, list) or len(choices) != 4 or
                not all(isinstance(c, str) and c.strip() for c in choices) or
                not isinstance(answers, list) or not answers or
                not all(type(a) is int and 0 <= a < 4 for a in answers) or
                len(set(answers)) != len(answers) or
                not isinstance(question.get("explanation"), str) or
                not question["explanation"].strip()):
            raise ValueError("Invalid generated question structure")
        if question.get("type") not in ("single", "multi") or (question["type"] == "single" and len(answers) != 1) or (question["type"] == "multi" and len(answers) < 2):
            raise ValueError("Invalid answer type")
        if not isinstance(question.get("sourceExcerpt"), str) or not question["sourceExcerpt"].strip():
            raise ValueError("Generated question lacks source support statement")
        excerpt = question["sourceExcerpt"].strip()
        matching_passages = [pid for pid, text in allowed_passages.items() if excerpt in text]
        # An exact source quotation establishes traceability, not medical correctness.
        # Paraphrases and invented excerpts remain unverified for human review.
        draft = {
            **question,
            "status": "draft",
            "candidateSourcePassageIds": payload["evidence"]["passage_ids"],
            "sourcePassageIds": matching_passages,
            "sourceExcerptMatch": "exact" if matching_passages else "unmatched",
            "evidenceVerificationStatus": "unverified",
            "citationVerified": False,
            "requiresHumanReview": True,
            "nceDomain": question.get("nceDomain"),
            "nceSection": question.get("nceSection"),
            "nceObjective": question.get("nceObjective"),
            "blueprintClassificationValid": validate_classification(question.get("nceDomain"), question.get("nceSection"), question.get("nceObjective")) and question.get("nceSection") is not None,
            "reasoningCategory": question.get("reasoningCategory"),
            "difficultyTier": question.get("difficultyTier"),
        }
        draft["boardQualityReview"] = review_item(draft, known_stems=[d["stem"] for d in drafts])
        if not draft["blueprintClassificationValid"]:
            draft["boardQualityReview"]["errors"].append("NBCRNA section/objective classification requires review")
        drafts.append(draft)
    return {"drafts": drafts, "count": len(drafts),
            "provider": raw.get("provider"), "model": raw.get("model"),
            "autoApproved": False, "sourceEvidence": payload["evidence"]}
