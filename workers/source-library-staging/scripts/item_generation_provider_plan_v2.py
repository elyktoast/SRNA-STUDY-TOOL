"""Staging-only, declarative AI routing policy; no network calls or secrets.

Quotas below reflect a project screenshot, not guaranteed remaining capacity.
Do not enable fallback until the provider adapter passes schema/evidence tests.
"""

STAGES = ("concept_card", "item_draft", "rationale")
MODEL_ALLOWLIST = {
    "gemini": frozenset(("gemini-3.5-flash-lite", "gemini-3.8-flash", "gemini-3.6-flash")),
    "groq": frozenset(("openai/gpt-oss-120b",)),
}
PROJECT_QUOTA_HINTS = {
    ("gemini", "gemini-3.5-flash-lite"): {"rpm": 15, "input_tpm": 250000, "rpd": 500},
    ("gemini", "gemini-3.8-flash"): {"rpm": 5, "input_tpm": 250000, "rpd": 20},
    ("gemini", "gemini-3.6-flash"): {"rpm": 5, "input_tpm": 250000, "rpd": 20},
}
DEFAULT_PLAN = {
    "concept_card": (("gemini", "gemini-3.5-flash-lite"),),
    "item_draft": (("groq", "openai/gpt-oss-120b"),),
    "rationale": (("groq", "openai/gpt-oss-120b"),),
}


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != set(STAGES):
        raise ValueError("Exactly three generation stages required")
    for stage in STAGES:
        candidates = plan[stage]
        if not isinstance(candidates, (tuple, list)) or not 1 <= len(candidates) <= 3:
            raise ValueError("Each stage requires one to three explicit providers")
        seen = set()
        for candidate in candidates:
            if (not isinstance(candidate, (tuple, list)) or len(candidate) != 2
                    or not all(isinstance(v, str) for v in candidate)):
                raise ValueError("Invalid provider/model pair")
            provider, model = candidate
            if model not in MODEL_ALLOWLIST.get(provider, ()) or (provider, model) in seen:
                raise ValueError("Unknown or duplicate provider/model")
            seen.add((provider, model))
    return {stage: tuple(tuple(candidate) for candidate in plan[stage]) for stage in STAGES}


def choose_provider(plan, stage, unavailable=()):
    validated = validate_plan(plan)
    if stage not in STAGES:
        raise ValueError("Unknown generation stage")
    blocked = set(unavailable)
    for provider, model in validated[stage]:
        if (provider, model) not in blocked:
            return {"provider": provider, "model": model,
                    "quota_hint": PROJECT_QUOTA_HINTS.get((provider, model))}
    return None
