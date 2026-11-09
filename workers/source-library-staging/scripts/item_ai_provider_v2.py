"""Opt-in, staging-only JSON AI adapter for isolated v2 question workflows.

Requires explicit owner authorization and an injected HTTPS transport. Credentials
and source excerpts must never be logged. Does not write to any database.
"""
import json
from urllib.parse import urlsplit

ALLOWED_STEPS = {"concept_card", "item_draft", "rationale", "rewrite", "blind_review"}

class ProviderError(RuntimeError):
    pass

def make_adapter(*, endpoint, api_key, model, transport, owner_opt_in=False,
                 staging=True, max_output_tokens=4096):
    if owner_opt_in is not True or staging is not True:
        raise ValueError("Explicit owner opt-in and staging isolation required")
    if not isinstance(endpoint, str) or urlsplit(endpoint).scheme != "https":
        raise ValueError("HTTPS provider endpoint required")
    url = urlsplit(endpoint)
    if not url.hostname or url.username or url.password or url.fragment or url.query or url.port not in (None, 443):
        raise ValueError("Invalid provider endpoint")
    if not isinstance(api_key, str) or not api_key.strip():
        raise ValueError("Provider credential required")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("Explicit model required")
    if not callable(transport):
        raise ValueError("Injected transport required")
    if type(max_output_tokens) is not int or not 256 <= max_output_tokens <= 8192:
        raise ValueError("Invalid output token limit")

    def adapter(request):
        if not isinstance(request, dict) or request.get("step") not in ALLOWED_STEPS:
            raise ValueError("Unsupported generation request")
        if request.get("rules_version") != "2.0" or request.get("auto_publish") is not False:
            raise ValueError("Unsafe generation contract")
        if request["step"] == "rewrite":
            if request.get("max_rewrites") != 1 or request.get("requires_human_review") is not True:
                raise ValueError("Unsafe rewrite contract")
            if not isinstance(request.get("item"), dict) or not isinstance(request.get("issues"), list):
                raise ValueError("Rewrite requires original item and diagnostics")
        if request["step"] == "blind_review":
            forbidden = {"key", "rationale", "distractor_evidence", "concept_card", "evidence"}
            if forbidden.intersection(request) or request.get("blind") is not True:
                raise ValueError("Blind review request contains forbidden fields")
            if not isinstance(request.get("item_id"), str) or not isinstance(request.get("stem"), str):
                raise ValueError("Blind review requires item ID and stem")
        if request["step"] == "blind_review":
            fmt = request.get("format")
            if fmt not in ("MC", "MS", "SA", "DD", "HS"):
                raise ValueError("Unsupported blind item format")
            allowed = {"step", "rules_version", "auto_publish", "blind",
                       "item_id", "format", "stem"}
            allowed.update({"options", "select_count"} if fmt in ("MC", "MS")
                           else {"unit", "rounding"} if fmt == "SA"
                           else {"left", "right"} if fmt == "DD"
                           else {"figure"})
            if set(request) - allowed:
                raise ValueError("Blind request includes non-blind fields")
            if fmt in ("MC", "MS"):
                options = request.get("options")
                if (not isinstance(options, list) or not options
                        or any(not isinstance(o, dict) or set(o) != {"id", "text"}
                               or not isinstance(o["id"], str) or not o["id"].strip()
                               or not isinstance(o["text"], str) or not o["text"].strip()
                               for o in options)):
                    raise ValueError("Blind choices must contain only IDs and text")
                if fmt == "MS" and request.get("select_count") not in (2, 3):
                    raise ValueError("Blind multi-select count required")
                if fmt == "MC" and request.get("select_count") is not None:
                    raise ValueError("Unexpected blind selection count")
            if fmt == "DD":
                for field in ("left", "right"):
                    entries = request.get(field)
                    if (not isinstance(entries, list) or not entries
                            or any(not (isinstance(e, str) and e.strip())
                                   and not (isinstance(e, dict) and set(e) == {"id", "text"}
                                            and isinstance(e["id"], str) and e["id"].strip()
                                            and isinstance(e["text"], str) and e["text"].strip())
                                   for e in entries)):
                        raise ValueError("Blind matching entries must contain only IDs and text")
            if fmt == "HS":
                figure = request.get("figure")
                if not isinstance(figure, (str, dict)) or (isinstance(figure, dict) and (not figure or set(figure) - {"url", "alt", "width", "height"})):
                    raise ValueError("Blind hotspot figure contains unsupported fields")
        # Step-specific ceilings reduce oversized generations without changing validation.
        step_caps = {"concept_card": 1200, "item_draft": 2600, "rationale": 1400, "rewrite": 3500, "blind_review": 1000}
        output_budget = min(max_output_tokens, step_caps[request["step"]])
        body = {"model": model, "messages": [
            {"role": "system", "content": "Return exactly one valid JSON object and no markdown. Follow the supplied NCE/SEE v2.0 step contract. For rewrite, return the complete corrected item and preserve protected metadata. For blind_review, independently solve the supplied item without a key or rationale: return item_id and key array for MC/MS, numeric_answer for SA, pairs for DD, or region for HS. Do not claim human verification."},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)}
        ], "max_tokens": output_budget, "temperature": 0.2}
        # Transport signature deliberately explicit. Caller enforces timeouts,
        # provider-specific authentication and retries.
        response = transport(endpoint=endpoint,
                             headers={"Authorization": "Bearer " + api_key,
                                      "Content-Type": "application/json"},
                             body=body)
        if not isinstance(response, dict):
            raise ProviderError("Provider response must be an object")
        try:
            content = response["choices"][0]["message"]["content"]
            if not isinstance(content, str) or len(content) > 262144:
                raise ValueError("Invalid provider content")
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Provider did not return a valid JSON object") from None
        if not isinstance(parsed, dict):
            raise ProviderError("Provider output must be a JSON object")
        # Some JSON-mode providers return the complete rewrite in an exact
        # single-key envelope. Unwrap transport structure only; protected
        # metadata, answer and citation checks still run on the candidate.
        if request["step"] == "rewrite" and isinstance(parsed.get("item"), dict):
            protocol = {"step": "rewrite", "rules_version": "2.0", "auto_publish": False,
                        "max_rewrites": 1, "requires_human_review": True, "can_publish": False}
            extras = set(parsed) - {"item"}
            if extras <= set(protocol) and all(type(parsed[k]) is type(protocol[k]) and parsed[k] == protocol[k] for k in extras):
                parsed = parsed["item"]
        return parsed
    return adapter
