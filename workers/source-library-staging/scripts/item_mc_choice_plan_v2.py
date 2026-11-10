"""Private MC planning invariants, never source/clinical approval."""
from copy import deepcopy


def validate(plan):
    fields = {"dimensions", "stem_condition", "alternate_condition", "key", "alternate_key", "options"}
    if not isinstance(plan, dict) or set(plan) != fields:
        raise ValueError("Concept card choice plan incomplete")
    def strings(values, count, bound):
        return (isinstance(values, list) and len(values) == count
                and all(isinstance(v, str) and v.strip() and len(v) <= bound for v in values))
    if (not strings(plan["dimensions"], 2, 80)
            or len({v.strip().casefold() for v in plan["dimensions"]}) != 2
            or not strings([plan["stem_condition"], plan["alternate_condition"]], 2, 200)
            or plan["stem_condition"].strip().casefold() == plan["alternate_condition"].strip().casefold()
            or not strings(plan["key"], 1, 1) or not strings(plan["alternate_key"], 1, 1)
            or plan["key"] == plan["alternate_key"]):
        raise ValueError("Concept card choice plan invalid")
    options = plan["options"]
    if (not isinstance(options, list) or len(options) != 4
            or any(not isinstance(o, dict) or set(o) != {"id", "text", "states"} for o in options)
            or [o["id"] for o in options] != list("ABCD")
            or any(k not in "ABCD" for k in plan["key"] + plan["alternate_key"])):
        raise ValueError("Concept card choice plan choices invalid")
    for option in options:
        if not strings([option["text"]], 1, 180) or not strings(option["states"], 2, 80):
            raise ValueError("Concept card choice plan response invalid")
    signatures = {tuple(" ".join(v.casefold().split()) for v in o["states"]) for o in options}
    if len(signatures) != 4 or len({o["text"].strip().casefold() for o in options}) != 4:
        raise ValueError("Concept card choice plan repeats a response pattern")
    return deepcopy(plan)


def bind(plan, draft):
    """Require the actual draft to use the plan; truth remains independently checked."""
    options = [{k:v for k,v in o.items() if k != "states"} for o in plan["options"]]
    actual = [{k:o.get(k) for k in ("id", "text")} for o in draft.get("options", []) if isinstance(o, dict)]
    if (draft.get("key") != plan["key"] or actual != options
            or draft["stem"].count(plan["stem_condition"]) != 1
            or plan["alternate_condition"] in draft["stem"]):
        raise ValueError("Generated draft differs from its choice plan")
    return {"from_text":plan["stem_condition"], "to_text":plan["alternate_condition"],
            "expected_key":deepcopy(plan["alternate_key"])}
