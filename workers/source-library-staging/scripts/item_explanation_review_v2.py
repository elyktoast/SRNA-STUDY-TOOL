"""Independent source-only checks of explanatory fields; never clinical approval."""
import re


def _exclusive_clinical_claim(field):
    label = field["label"]
    if label not in ("concept_card.mechanism", "rationale.core_concept") and not label.startswith(
            ("rationale.distractor_breakdown.", "distractor_evidence.")):
        return False
    return bool(re.search(r"\b(?:are|is)\s+(?:the\s+)?(?:only|sole)\s+(?:[A-Za-z-]+\s+){0,3}"
                          r"(?:agents?|drugs?|causes?|mechanisms?|triggers?|treatments?|pathways?)\b",
                          field["text"], re.I) or re.match(r"\s*Only\b", field["text"], re.I))


def _source_silence_claim(field):
    if not field["label"].startswith(("rationale.distractor_breakdown.", "distractor_evidence.")):
        return False
    return bool(re.search(
        r"\bwithout mentioning\b|\bno statement about\b|"
        r"\b(?:source|passage|textbook|excerpt)\s+(?:does not|doesn't|do not|never)\s+(?:mention|state|describe|support)\b",
        field["text"], re.I))


def fields_for(item):
    fields = []
    for section, names in (("concept_card", ("mechanism", "relevance", "misconception", "counterfactual")),
                           ("rationale", ("core_concept", "why_key_wins", "trap"))):
        for name in names:
            text = item.get(section, {}).get(name)
            if not isinstance(text, str) or not text.strip():
                raise ValueError("Complete explanatory text required")
            if section == "concept_card" and name == "counterfactual":
                # The separate changed-stem blind test grades the option mapping.
                # Here check both clinical premises, not whether a textbook names
                # our answer letters. Match only the complete server-rendered form;
                # never trim arbitrary appended claims from teaching text.
                match = re.fullmatch(r'If "(.{1,200})" is replaced by "(.{1,200})", the best response changes to option(?:\(s\))? [A-F](?:, [A-F])*\.', text)
                if match:
                    text = f'Original clinical condition: {match[1]}. Replacement clinical condition: {match[2]}.'
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
    for field in fields:
        field["assessment"] = ("misconception_to_refute" if field["label"] == "concept_card.misconception"
            else "teaching_application" if field["label"] in ("concept_card.relevance", "concept_card.counterfactual", "rationale.trap")
            else "clinical_fact")
    return fields


def review(item, sources, reviewer, *, batch_size=None):
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
        size = len(fields) if batch_size is None else batch_size
        if type(size) is not int or size < 1 or (batch_size is not None and size > 50):
            raise ValueError("Invalid explanatory batch size")
        result = {"supported_groups":[], "unsupported":[]}
        # A grouped answer may cite only sources allowed by every field in it.
        # Partition before calling the model; never broaden field citations.
        by_sources = {}
        for field in fields:
            by_sources.setdefault(tuple(field["passage_ids"]), []).append(field)
        batches = [group[i:i+size] for group in by_sources.values()
                   for i in range(0, len(group), size)]
        for batch in batches:
            batch_ids = {f["id"] for f in batch}
            source_ids = {pid for f in batch for pid in f["passage_ids"]}
            part = reviewer({"step": "explanation_review", "rules_version": "2.0",
                "auto_publish": False, "independent": True, "fields": batch,
                "source_passages": [p for p in packet["source_passages"] if p["passage_id"] in source_ids]})
            if (not isinstance(part, dict) or set(part) != {"supported_groups", "unsupported"}
                    or not isinstance(part["supported_groups"], list) or not isinstance(part["unsupported"], list)):
                raise ValueError("Incomplete explanatory review")
            returned = [fid for g in part["supported_groups"] for fid in g["field_ids"]] + [f["field_id"] for f in part["unsupported"]]
            if len(returned) != len(batch_ids) or set(returned) != batch_ids:
                raise ValueError("Every explanatory field must be reviewed")
            result["supported_groups"].extend(part["supported_groups"])
            result["unsupported"].extend(part["unsupported"])
        if not isinstance(result, dict) or set(result) != {"supported_groups", "unsupported"}:
            raise ValueError("Incomplete explanatory review")
        if not isinstance(result["supported_groups"], list) or not isinstance(result["unsupported"], list):
            raise ValueError("Invalid explanatory judgments")
        expected = {f["id"]: f["label"] for f in fields}
        exclusive = {f["id"] for f in fields if _exclusive_clinical_claim(f)}
        seen, evidence = set(), []
        issues = [{"rule_id":"R-2.4", "field":f["label"],
                   "message":"Source silence cannot establish that this option is false; affirmative contradiction is required"}
                  for f in fields if _source_silence_claim(f)]
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
                if fid in exclusive and not any(re.search(r"\b(?:only|sole|exclusively|exhaustive)\b", q["quote"], re.I) for q in quotes):
                    issues.append({"rule_id":"R-2.4", "field":expected[fid],
                                   "message":"Exclusive clinical wording lacks explicit exclusivity in its cited supporting quotation"})
            flagged = {issue["field"] for issue in issues}
            supported = [expected[fid] for fid in ids if expected[fid] not in flagged]
            if supported:
                evidence.append({"fields": supported, "quotes": quotes})
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
                "checked_fields": list(expected.values()), "source_support": evidence, "batch_count":len(batches)}
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
