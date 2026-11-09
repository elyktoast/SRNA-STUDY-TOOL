"""Independent source-only checks of explanatory fields; never clinical approval."""


def fields_for(item):
    fields = []
    for section, names in (("concept_card", ("mechanism", "relevance", "misconception", "counterfactual")),
                           ("rationale", ("core_concept", "why_key_wins", "trap"))):
        for name in names:
            text = item.get(section, {}).get(name)
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Complete explanatory text required")
            fields.append({"id": "e" + str(len(fields)), "label": section + "." + name, "text": text})
    for oid, text in item.get("rationale", {}).get("distractor_breakdown", {}).items():
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Complete option explanations required")
        fields.append({"id": "e" + str(len(fields)), "label": "rationale.distractor_breakdown." + oid, "text": text})
    for oid, entry in item.get("distractor_evidence", {}).items():
        text = entry.get("explanation") if isinstance(entry, dict) else None
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Complete option evidence explanations required")
        fields.append({"id": "e" + str(len(fields)), "label": "distractor_evidence." + oid, "text": text})
    return fields


def review(item, sources, reviewer):
    """The caller supplies a distinct authenticated model; outages stay pending."""
    pending = {"status": "pending", "issues": [], "can_publish": False,
               "clinical_truth_verified": False, "human_review_required": True}
    try:
        fields = fields_for(item)
        # Only source passages actually cited by this question may justify it.
        cited = {e["passage_id"] for e in item.get("evidence", [])}
        trusted = [p for p in sources if p["passage_id"] in cited]
        if not trusted or len(trusted) != len(cited):
            raise ValueError("Cited indexed explanatory evidence unavailable")
        from item_source_quote_spans_v2 import prepare
        packet, lookup = prepare({"source_passages": trusted})
        allowed = {}
        for field in fields:
            label = field["label"]
            ids = (item.get("concept_card", {}).get("evidence_ids", list(cited))
                   if label.startswith("concept_card.") else
                   item.get("distractor_evidence", {}).get(label.rsplit(".", 1)[-1], {}).get("passage_ids", list(cited))
                   if label.startswith(("rationale.distractor_breakdown.", "distractor_evidence.")) else list(cited))
            allowed[field["id"]] = set(ids)
        for field in fields:
            field["passage_ids"] = sorted(allowed[field["id"]] & cited)
        result = reviewer({"step": "explanation_review", "rules_version": "2.0",
                           "auto_publish": False, "independent": True,
                           "fields": fields, "source_passages": packet["source_passages"]})
        if not isinstance(result, dict) or set(result) != {"supported_groups", "unsupported"}:
            raise ValueError("Incomplete explanatory review")
        if not isinstance(result["supported_groups"], list) or not isinstance(result["unsupported"], list):
            raise ValueError("Invalid explanatory judgments")
        expected = {f["id"]: f["label"] for f in fields}
        seen, evidence, issues = set(), [], []
        for group in result["supported_groups"]:
            if not isinstance(group, dict) or set(group) != {"field_ids", "quote_refs"}:
                raise ValueError("Invalid supported fields")
            ids, refs = group["field_ids"], group["quote_refs"]
            if not isinstance(ids, list) or not ids or not isinstance(refs, list) or not 1 <= len(refs) <= 8:
                raise ValueError("Missing source support")
            quotes = []
            for ref in refs:
                if not isinstance(ref, dict) or set(ref) != {"passage_id", "span_id"}:
                    raise ValueError("Invalid source span")
                pid, sid = ref["passage_id"], ref["span_id"]
                if not isinstance(pid, str) or not isinstance(sid, str) or pid not in lookup or sid not in lookup[pid]:
                    raise ValueError("Unknown source span")
                quote = lookup[pid][sid]
                if not 6 <= len(quote) <= 300:
                    raise ValueError("Source quote outside bounds")
                quotes.append({"passage_id": pid, "quote": quote})
            for fid in ids:
                if not isinstance(fid, str) or fid not in expected or fid in seen:
                    raise ValueError("Missing, repeated or unknown explanatory field")
                if any(q["passage_id"] not in allowed[fid] for q in quotes):
                    raise ValueError("Support not cited for this explanatory field")
                seen.add(fid)
            evidence.append({"fields": [expected[fid] for fid in ids], "quotes": quotes})
        for finding in result["unsupported"]:
            if not isinstance(finding, dict) or set(finding) != {"field_id", "reason"}:
                raise ValueError("Invalid unsupported finding")
            fid, reason = finding["field_id"], finding["reason"]
            if (not isinstance(fid, str) or fid not in expected or fid in seen
                    or not isinstance(reason, str) or not reason.strip() or len(reason) > 400):
                raise ValueError("Invalid unsupported field")
            seen.add(fid)
            issues.append({"rule_id": "R-2.4", "field": expected[fid],
                           "message": "Explanatory claim lacks affirmative indexed support: " + reason.strip()})
        if seen != set(expected):
            raise ValueError("Every explanatory field must be reviewed")
        return {**pending, "status": "flag" if issues else "pass", "issues": issues,
                "checked_fields": list(expected.values()), "source_support": evidence}
    except Exception as exc:
        rule = getattr(exc, "rule", "REVIEW_RESPONSE_INVALID")
        allowed = {"PROVIDER_RATE_LIMIT", "PROVIDER_TIMEOUT", "PROVIDER_UPSTREAM", "PROVIDER_AUTH", "PROVIDER_FORBIDDEN"}
        # Only fixed local validation messages may become diagnostics.
        messages = {"Incomplete explanatory review", "Invalid explanatory judgments",
                    "Invalid supported fields", "Missing source support", "Invalid source span",
                    "Unknown source span", "Source quote outside bounds",
                    "Missing, repeated or unknown explanatory field",
                    "Support not cited for this explanatory field", "Invalid unsupported finding",
                    "Invalid unsupported field", "Every explanatory field must be reviewed"}
        return {**pending, "provider_rule": rule if rule in allowed else "REVIEW_RESPONSE_INVALID",
                "review_error": str(exc) if type(exc) is ValueError and str(exc) in messages else None}
