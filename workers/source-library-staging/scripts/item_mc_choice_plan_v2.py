"""Private MC planning invariants; rendering never proves clinical correctness."""
from copy import deepcopy
import re

CONDITION_SLOT = "{{STEM_CONDITION}}"


def render_condition(plan, draft):
    """Insert the authored case literally; never infer or repair clinical prose."""
    stem = draft.get("stem")
    if not isinstance(stem, str) or CONDITION_SLOT not in stem:
        return draft  # Older literal drafts still have to pass strict bind().
    if (stem.count(CONDITION_SLOT) != 1
            or plan["stem_condition"] in stem
            or plan["alternate_condition"] in stem):
        raise ValueError("Generated draft differs from its choice plan: condition")
    return {**draft, "stem": stem.replace(CONDITION_SLOT, plan["stem_condition"])}


def validate(plan):
    fields = {"response_variables", "stem_condition", "alternate_condition", "key", "alternate_key", "options"}
    if not isinstance(plan, dict) or set(plan) != fields:
        raise ValueError("Concept card choice plan incomplete")

    def strings(values, count, bound):
        return (isinstance(values, list) and len(values) == count
                and all(isinstance(v, str) and v.strip() and len(v) <= bound for v in values))

    normalize = lambda value: " ".join(value.split())
    if (not strings(plan["response_variables"], 2, 80)
            or len({normalize(v).casefold() for v in plan["response_variables"]}) != 2
            or not strings([plan["stem_condition"], plan["alternate_condition"]], 2, 200)
            or normalize(plan["stem_condition"]).casefold() == normalize(plan["alternate_condition"]).casefold()
            or not strings(plan["key"], 1, 1) or not strings(plan["alternate_key"], 1, 1)
            or plan["key"] == plan["alternate_key"]):
        raise ValueError("Concept card choice plan invalid")
    metadata_axes = {"type", "measurement type", "compliance type", "direction", "direction of change",
                     "change direction", "state", "value", "name", "option", "answer", "response"}
    if any(normalize(v).casefold() in metadata_axes for v in plan["response_variables"]):
        raise ValueError("Concept card choice plan response_variables are not clinical components")
    for condition in (plan["stem_condition"], plan["alternate_condition"]):
        if any(re.search(r"(?<!\w)" + re.escape(normalize(variable).casefold()) + r"(?!\w)",
                         normalize(condition).casefold()) for variable in plan["response_variables"]):
            raise ValueError("Concept card condition gives away a planned response")
    options = plan["options"]
    if (not isinstance(options, list) or len(options) != 4
            or any(not isinstance(o, dict) or set(o) not in ({"id", "states"}, {"id", "text", "states"}) for o in options)
            or [o["id"] for o in options] != list("ABCD")
            or any(k not in "ABCD" for k in plan["key"] + plan["alternate_key"])):
        raise ValueError("Concept card choice plan choices invalid")
    if any(not strings(o["states"], 2, 80) for o in options):
        raise ValueError("Concept card choice plan response invalid")
    signatures = {tuple(normalize(v).casefold() for v in o["states"]) for o in options}
    if len(signatures) != 4:
        raise ValueError("Concept card choice plan repeats a response pattern")
    result = deepcopy(plan)
    result["response_variables"] = [normalize(v) for v in plan["response_variables"]]
    for option in result["options"]:
        option["states"] = [normalize(v) for v in option["states"]]
        # Models sometimes repeat the literal component label inside its state.
        # Remove that repeated label only; never infer or change the state.
        for index, component in enumerate(result["response_variables"]):
            state = option["states"][index]
            repeated = re.match(re.escape(component) + r"(?:\s*:\s*|\s+)(.+)$", state, re.I)
            if repeated:
                option["states"][index] = repeated[1]
        text = "; ".join(f"{component}: {state}" for component, state in zip(result["response_variables"], option["states"]))
        if len(text) > 180:
            raise ValueError("Concept card choice plan response invalid")
        # Checkpoints may contain the previously rendered text. It must match;
        # never silently replace a changed clinical response in a resumed plan.
        if "text" in option and option["text"] != text:
            raise ValueError("Concept card choice plan rendered response differs")
        option["text"] = text
    if len({tuple(v.casefold() for v in o["states"]) for o in result["options"]}) != 4:
        raise ValueError("Concept card choice plan repeats a response pattern")
    return result


def bind(plan, draft):
    """Bind rendered choices, not their clinical truth, to the actual draft."""
    options = [{"id":o["id"], "text":o["text"]} for o in plan["options"]]
    actual = draft.get("options")
    if not isinstance(actual, list) or len(actual) != 4 or any(not isinstance(o, dict) for o in actual):
        raise ValueError("Generated draft differs from its choice plan")
    actual = [{k:o.get(k) for k in ("id", "text")} for o in actual]
    if draft.get("key") != plan["key"]:
        raise ValueError("Generated draft differs from its choice plan: key")
    if actual != options:
        raise ValueError("Generated draft differs from its choice plan: choices")
    if (draft["stem"].count(plan["stem_condition"]) != 1
            or plan["alternate_condition"] in draft["stem"]):
        raise ValueError("Generated draft differs from its choice plan: condition")
    return {"from_text":plan["stem_condition"], "to_text":plan["alternate_condition"],
            "expected_key":deepcopy(plan["alternate_key"])}
