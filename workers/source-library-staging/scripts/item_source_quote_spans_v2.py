"""Trusted quote-span references for independent source review.

The model selects spans and judges options. Only the server copies source text;
neither clinical verdicts nor the keyed answer are supplied or corrected here.
"""
import copy


def prepare(request):
    sources = []
    lookup = {}
    for passage in request["source_passages"]:
        pid, excerpt = passage.get("passage_id"), passage.get("excerpt")
        if not isinstance(pid, str) or not pid or pid in lookup or not isinstance(excerpt, str):
            raise ValueError("Invalid trusted review source")
        spans = []
        for raw_line in excerpt.splitlines():
            line = raw_line.strip()
            while line:
                end = min(len(line), 300)
                if end < len(line):
                    boundary = line.rfind(" ", 0, end)
                    if boundary >= 6:
                        end = boundary
                text = line[:end].strip()
                if len(text) >= 6:
                    spans.append({"id": "q" + str(len(spans)), "text": text})
                line = line[end:].strip()
        if not spans:
            raise ValueError("Source has no quotable indexed spans")
        lookup[pid] = {span["id"]: span["text"] for span in spans}
        sources.append({"passage_id": pid, "quote_spans": spans})
    return {**request, "source_passages": sources}, lookup


def hydrate(response, request, lookup):
    # Legacy exact quotes retain the unchanged downstream verbatim check.
    result = copy.deepcopy(response)
    judgments = result.get("judgments")
    if not isinstance(judgments, list):
        raise ValueError("Independent judgments required")
    allowed = {a["option_id"]: set(a["retrieved_passage_ids"])
               for a in request["retrieval"]["option_audits"]}
    for judgment in judgments:
        if not isinstance(judgment, dict):
            raise ValueError("Invalid independent judgment")
        if "quote_refs" not in judgment:
            continue
        refs = judgment.pop("quote_refs")
        if ("quotes" in judgment or not isinstance(refs, list) or not 1 <= len(refs) <= 8):
            raise ValueError("Invalid source quote references")
        quotes = []
        for ref in refs:
            if not isinstance(ref, dict) or set(ref) != {"passage_id", "span_id"}:
                raise ValueError("Invalid source quote reference")
            pid, sid = ref["passage_id"], ref["span_id"]
            if (not isinstance(pid, str) or not isinstance(sid, str)
                    or pid not in allowed.get(judgment.get("option_id"), set())
                    or pid not in judgment.get("passage_ids", [])
                    or pid not in lookup or sid not in lookup[pid]):
                raise ValueError("Unknown or unauthorized source quote reference")
            quotes.append(lookup[pid][sid])
        judgment["quotes"] = quotes
    return result
