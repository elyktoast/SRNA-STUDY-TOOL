"""One-rewrite limit for unpublished v2 draft repair.

The caller supplies a trusted rewrite callable. No network or database writes.
A failed rewrite remains flagged for human review; never auto-approves.
"""
from copy import deepcopy


def attempt_once(original, issues, rewrite, validate):
    if not isinstance(original, dict) or not isinstance(issues, list):
        raise ValueError("Original draft and diagnostic list required")
    if not callable(rewrite) or not callable(validate):
        raise ValueError("Explicit rewrite and validation callables required")
    if not issues:
        return {"item": deepcopy(original), "issues": [],
                "rewrite_attempts": 0, "can_publish": False}
    immutable = ("item_id", "rules_version", "mode", "domain", "section",
                 "objective", "format", "model", "status",
                 "numbers_verified_against_page_image")
    request = {"item": deepcopy(original), "issues": deepcopy(issues),
               "protected_metadata": {field: deepcopy(original.get(field)) for field in immutable},
               "required_output_keys": list(original),
               "max_rewrites": 1, "requires_human_review": True,
               "repair_instructions": (
                   "For R-12.1 with expected_key and independent_key, inspect the literal question and each independently selected option for ambiguity. expected_key is the protected author key, not proof of clinical correctness. independent_key is diagnostic feedback, not an instruction to change that key or force a reviewer to agree. Refine the stem or replace only an incorrect option using affirmative source support. Distinguish a device's clinically reported measurement from the physical sensing principle of its transducer; do not use directly measured when the sources and stem leave those levels ambiguous. If the evidence cannot establish a unique protected answer, leave the item held. "
                   "For R-2.8, paraphrase the copied wording in the indicated field. word_start is a zero-based token offset and word_count identifies the consecutive source words. Preserve the clinical facts and the protected key text. If the stem wording changes, update its literal phrase in concept_card.counterfactual and rationale.counterfactual_test.from_text so the alternate-case edit still matches the revised stem; preserve the alternate case and its different answer. Check the complete stem and every option against trusted source text for any remaining eight-word runs before returning. Never repair source-copying by changing the clinical answer. "
                   "For a counterfactual failure, inspect the ENTIRE alternate-key option: changing the case cannot make an inherently false explanation true. Replace an incorrect option's false justification with a source-supported response valid in the alternate case, while keeping it false in the original case. Do not balance option lengths by adding because, thereby, so that, or other explanatory rationales; explanations belong only in the rationale. "
                   "If an R-5.3 issue supplies stem_change, expected_key and independent_key, use that exact failed test as feedback. A changed diagnosis can leave the same mechanism responsible for a shared global outcome. Check what the common lead-in actually asks, including the affected compartment, measured variable and timing; do not merely add more alternate-case findings. Refine the common lead-in to the same precise source-supported task in both cases when necessary, preserving the original clinical answer and protected keyed text. Never force the observed reviewer answer or change the key just to pass. "
                   "For R-5.3, quote the exact original stem condition and its replacement in concept_card.counterfactual. The server will change only that stem phrase and a fresh blind solver must choose a different existing option. Check the ENTIRE edited stem for contradictions: pressure observations, laboratory findings, diagnostic labels and all other consequences of the original condition must be removed as redundant or included in the complete replaceable phrase with their alternate values. For MC, check the grammar of both complete stems. When the case precedes the lead-in, write the case as a complete sentence with its own initial capital and terminal period, then begin the question as a separate sentence. Also inspect the lead-in: replace references to an original-only symptom, drug or event with a neutral reference valid in both cases; changing the case while leaving the question about the old symptom is invalid. Keep the original case clinically consistent and preserve its protected key and keyed text. Tie the counterfactual to a variable actually used in the stem and state a different correct response; a restatement or changed option is insufficient. For R-12.2, remove answer cues by making the INCORRECT options plausible competing answers under the same patient, exposure and requested category. Do not offer unrelated drug or population trivia that is excluded just by matching names in the stem. Keep the protected keyed text unchanged and ground every replacement distractor in evidence. For R-9, explicitly name the incorrect option ID (for example, Option C), then explain that plausible distractor and the specific error that truly leads to selecting it. For R-8.5 in text-only MC/MS, remove equations, formula definitions, doses and unnecessary numeric measurements; keep the directly source-supported qualitative mechanism and never invent page-image verification. For R-8.4, remove obsolete authored drug/test examples unless explicitly historical. Fix only the reported rule-ID issues. Copy every protected_metadata field EXACTLY, including null values, and preserve the question's "
                   "clinical meaning, answer key, protected metadata, concept "
                   "evidence IDs, and all unaffected fields. For MC source failures, use another supplied passage when the original citation cannot establish the flagged distinction. Prefer a single supported reason tied to the distractor itself. When a cited alarm threshold is enough to refute a choice, explain that the case does not meet that threshold. Do not add a categorical negative claim about another signal the device cannot measure if the passage establishes only the trigger. Remove comparisons that require a separate, uncited mechanism. If a second clinical claim is indispensable, include a passage supporting it in that option’s passage_ids and the item evidence array. If a distractor cannot be affirmatively ruled out under the exact case, replace it with a plausible peer that can be. When changing an option, update its explanation, evidence map, citation and any trap that references it together. For R-4.2 incomplete case sentences, finish or simplify the thought before the separate question. Aim for 150 characters or fewer for each complete condition to leave room below the 200-character limit. Never cut a sentence to fit. Update the exact original and alternate counterfactual phrases to match without changing the answer. For R-2.4 explanatory claims, replace the flagged mechanism, relevance, counterfactual or rationale text with what its cited excerpt affirmatively supports; remove unsupported background rather than preserving or inventing it. Preserve the stem and answer meaning. For R-6.8, leave the keyed option text EXACTLY unchanged and balance the incorrect options to similar lengths using evidence-grounded single-flaw alternatives; never shorten or edit the protected key. For R-2.5, use only "
                   "exact verbatim excerpts and matching source IDs/pages from "
                   "trusted evidence; never invent a citation. For R-12.4, give "
                   "every option an evidence-grounded verdict, valid passage IDs, "
                   "and an explanation; source silence cannot refute a distractor. "
                    "If an option is ambiguous, potentially also correct, or its explanation lacks affirmative source support, repair the STEM conditions or replace the INCORRECT option with a distinct clinically plausible, demonstrably false alternative; never change the protected correct answer or its text. Supply a separate evidence-grounded explanation for EVERY option, including the correct one, and update distractor_evidence and rationale consistently. Do not infer that an answer is false just because a passage does not mention it. If the supplied evidence is insufficient, do not fabricate "
                   "a repair. Return the complete revised item as a JSON object. "
                   "The result remains unpublished and requires clinical review."
               )}
    try:
        candidate = rewrite(request)
    except Exception:
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    if not isinstance(candidate, dict):
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    if any(candidate.get(field) != original.get(field) for field in immutable):
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-13", "message": "Rewrite attempted to change protected metadata"}] + deepcopy(issues),
            "rewrite_attempts": 1, "can_publish": False}
    # A rule-specific rewrite must not silently alter the answer.
    if candidate.get("key") != original.get("key"):
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-5.1", "message": "Rewrite changed answer key"}] + deepcopy(issues),
            "rewrite_attempts": 1, "can_publish": False}
    if original.get("format") in ("MC", "MS"):
        def keyed_texts(item):
            options = item.get("options")
            if not isinstance(options, list):
                return None
            lookup = {o.get("id"): o.get("text") for o in options if isinstance(o, dict)}
            return [lookup.get(k) for k in original.get("key", [])]
        if keyed_texts(candidate) != keyed_texts(original):
            return {"item": deepcopy(original), "issues": [
                {"rule_id": "R-5.1", "message": "Rewrite changed keyed option text"}] + deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False}
    for fmt, field, answer_field in (
            ("SA", "sa", "answer"), ("DD", "dd", "pairs"),
            ("HS", "hs", "correct_region")):
        if original.get("format") == fmt:
            before, after = original.get(field), candidate.get(field)
            if not isinstance(before, dict) or not isinstance(after, dict) or before.get(answer_field) != after.get(answer_field):
                return {"item": deepcopy(original), "issues": [
                    {"rule_id": "R-5.1", "message": "Rewrite changed protected answer"}] + deepcopy(issues),
                    "rewrite_attempts": 1, "can_publish": False}
    prior = original.get("concept_card")
    revised = candidate.get("concept_card")
    if isinstance(prior, dict) and (
            not isinstance(revised, dict) or
            prior.get("evidence_ids") != revised.get("evidence_ids")):
        return {"item": deepcopy(original), "issues": deepcopy(issues) + [
            {"rule_id": "R-2.5", "message": "Rewrite changed concept evidence references"}],
            "rewrite_attempts": 1, "can_publish": False}
    if candidate.get("status") != "draft":
        return {"item": deepcopy(original), "issues": [
            {"rule_id": "R-13", "message": "Rewrite cannot change draft review state"}] + deepcopy(issues),
            "rewrite_attempts": 1, "can_publish": False}
    try:
        checked = validate(deepcopy(candidate))
    except Exception:
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    if not isinstance(checked, list):
        return {"item": deepcopy(original), "issues": deepcopy(issues),
                "rewrite_attempts": 1, "can_publish": False,
                "rewrite_failed": True}
    return {"item": deepcopy(candidate), "issues": checked,
            "rewrite_attempts": 1, "can_publish": False}
