"""Private MC planning invariants; rendering never proves clinical correctness."""
from copy import deepcopy
import re

CONDITION_SLOT = "{{STEM_CONDITION}}"
LEAD_IN_SLOT = "{{LEAD_IN}}"


def render_condition(plan, draft):
    """Insert the authored case literally; never infer or repair clinical prose."""
    stem = draft.get("stem")
    if not isinstance(stem, str) or (CONDITION_SLOT not in stem and LEAD_IN_SLOT not in stem):
        return draft  # Older literal drafts still have to pass strict bind().
    if stem not in (CONDITION_SLOT + " " + LEAD_IN_SLOT,
                    CONDITION_SLOT + " " + plan["lead_in"]):
        raise ValueError("Generated draft differs from its choice plan: condition")
    return {**draft, "stem": plan["stem_condition"] + " " + plan["lead_in"]}


def validate(plan, evidence=None):
    fields = {"response_variables", "stem_condition", "alternate_condition", "lead_in", "key", "alternate_key", "options", "option_grounding"}
    if not isinstance(plan, dict) or set(plan) != fields:
        raise ValueError("Concept card choice plan incomplete")

    def strings(values, count, bound):
        return (isinstance(values, list) and len(values) == count
                and all(isinstance(v, str) and v.strip() and len(v) <= bound for v in values))

    normalize = lambda value: " ".join(value.split())
    components = plan['response_variables']
    count = len(components) if isinstance(components, list) else 0
    if (count not in (1, 2) or not strings(components, count, 80)
            or len({normalize(v).casefold() for v in components}) != count
            or not strings([plan["stem_condition"], plan["alternate_condition"]], 2, 200)
            or not strings([plan["lead_in"]], 1, 200)
            or not plan["lead_in"].rstrip().endswith("?")
            or normalize(plan["stem_condition"]).casefold() == normalize(plan["alternate_condition"]).casefold()
            or not strings(plan["key"], 1, 1) or not strings(plan["alternate_key"], 1, 1)
            or plan["key"] == plan["alternate_key"]):
        raise ValueError("Concept card choice plan invalid")
    if any(condition in plan["lead_in"] for condition in
           (plan["stem_condition"], plan["alternate_condition"])):
        raise ValueError("Concept card lead-in repeats a clinical condition")
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
    if any(not isinstance(o['states'],list) or len(o['states']) != count for o in options):
        raise ValueError('Concept card choice plan state count differs from components')
    if any(not strings(o["states"], count, 80) for o in options):
        raise ValueError('Concept card choice plan states exceed text bounds')
    signatures = {tuple(normalize(v).casefold() for v in o["states"]) for o in options}
    if len(signatures) != 4:
        raise ValueError("Concept card choice plan repeats a response pattern")
    grounding = plan["option_grounding"]
    if not isinstance(grounding, dict) or set(grounding) != set("ABCD"):
        raise ValueError("Concept card option grounding incomplete")
    sources = None
    if evidence is not None:
        from item_source_quote_spans_v2 import prepare
        _, sources = prepare({"source_passages": evidence})
    for entry in grounding.values():
        if (not isinstance(entry, dict) or set(entry) != {"passage_id", "span_ids", "explanation"}
                or not strings([entry["passage_id"]], 1, 200)
                or not isinstance(entry["span_ids"], list) or not 1 <= len(entry["span_ids"]) <= 3
                or not strings(entry["span_ids"], len(entry["span_ids"]), 20)
                or len(set(entry["span_ids"])) != len(entry["span_ids"])
                or not strings([entry["explanation"]], 1, 700)):
            raise ValueError("Concept card option grounding invalid")
        # A real quote is a transport invariant, never a clinical judgment.
        if sources is not None and (entry["passage_id"] not in sources or
                any(sid not in sources[entry["passage_id"]] for sid in entry["span_ids"])):
            raise ValueError("Concept card option grounding span not in source")
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
        text = (option['states'][0] if count == 1 else
                "; ".join(f"{component}: {state}" for component, state in zip(result["response_variables"], option["states"])))
        if len(text) > 180:
            raise ValueError('Concept card choice plan rendered option exceeds text bounds')
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
    if draft["stem"] != plan["stem_condition"] + " " + plan["lead_in"]:
        raise ValueError("Generated draft differs from its choice plan: lead-in")
    return {"from_text":plan["stem_condition"], "to_text":plan["alternate_condition"],
            "expected_key":deepcopy(plan["alternate_key"])}


def option_explanations(plan):
    return {oid: entry["explanation"] for oid, entry in plan["option_grounding"].items()}


def ground_draft(plan, draft):
    """Carry the author's locked explanations forward; do not adjudicate them."""
    mapping = {oid: {"verdict": "supports_key" if oid in plan["key"] else "refutes_distractor",
                     "passage_ids": [entry["passage_id"]], "explanation": entry["explanation"]}
               for oid, entry in plan["option_grounding"].items()}
    if "distractor_evidence" in draft and draft["distractor_evidence"] != mapping:
        raise ValueError("Generated draft differs from its choice plan: grounding")
    return {**draft, "distractor_evidence": mapping}
