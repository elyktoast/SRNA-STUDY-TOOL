#!/usr/bin/env python3
"""Private backend orchestration: indexed evidence -> existing generator -> review drafts.

The caller supplies a short-lived, authenticated staging JWT. Never log tokens,
source passages, or generated medical content. No questions are auto-approved.
"""
import json
import urllib.error
import urllib.request

from prepare_grounded_generation import prepare


def generate_drafts(conn, owner_uid, topic, *, endpoint, jwt, apikey,
                    textbook_id=None, count=5, transport=None):
    if not isinstance(endpoint, str) or not endpoint.startswith("https://"):
        raise ValueError("HTTPS generator endpoint required")
    if not endpoint.rstrip("/").endswith("/functions/v1/generate-questions"):
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
        drafts.append({
            **question,
            "status": "draft",
            "sourcePassageIds": payload["evidence"]["passage_ids"],
            "citationVerified": False,
            "requiresHumanReview": True,
        })
    return {"drafts": drafts, "count": len(drafts),
            "provider": raw.get("provider"), "model": raw.get("model"),
            "autoApproved": False, "sourceEvidence": payload["evidence"]}
