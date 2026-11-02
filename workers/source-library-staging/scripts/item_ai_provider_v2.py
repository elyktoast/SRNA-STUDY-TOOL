"""Opt-in, staging-only JSON AI adapter for isolated v2 question workflows.

Requires explicit owner authorization and an injected HTTPS transport. Credentials
and source excerpts must never be logged. Does not write to any database.
"""
import json
from urllib.parse import urlsplit

ALLOWED_STEPS = {"concept_card", "item_draft", "rationale"}

class ProviderError(RuntimeError):
    pass

def make_adapter(*, endpoint, api_key, model, transport, owner_opt_in=False,
                 staging=True, max_output_tokens=4096):
    if owner_opt_in is not True or staging is not True:
        raise ValueError("Explicit owner opt-in and staging isolation required")
    if not isinstance(endpoint, str) or urlsplit(endpoint).scheme != "https":
        raise ValueError("HTTPS provider endpoint required")
    url = urlsplit(endpoint)
    if not url.hostname or url.username or url.password or url.fragment:
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
        body = {"model": model, "messages": [
            {"role": "system", "content": "Return exactly one valid JSON object and no markdown. Follow the supplied NCE/SEE v2.0 step contract. Do not claim human verification."},
            {"role": "user", "content": json.dumps(request, ensure_ascii=False)}
        ], "max_tokens": max_output_tokens, "temperature": 0.2}
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
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Provider did not return a valid JSON object") from None
        if not isinstance(parsed, dict):
            raise ProviderError("Provider output must be a JSON object")
        return parsed
    return adapter
