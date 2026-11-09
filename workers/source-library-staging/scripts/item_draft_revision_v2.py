"""Build a human-reviewable draft revision proposal without database mutation.

This intentionally does not claim that indexed citations establish clinical truth.
Only a subsequent authenticated, versioned persistence operation may save it.
"""
from copy import deepcopy
from item_generation_runner_v2 import _complete_nonclinical_schema_fields
from item_source_reconciliation_v2 import reconcile
from item_answer_evidence_v2 import check as check_answers
from item_special_format_evidence_v2 import check as check_special
from item_generation_contract_v2 import validate_complete_item


def propose_revision(draft, trusted_passages, *, citation_excerpts=None,
                     option_evidence=None, question_edits=None):
    if not isinstance(draft, dict) or draft.get("published") is not False or draft.get("status") not in ("pending_review", "needs_revision"):
        raise ValueError("Only unpublished review drafts may be revised")
    if not isinstance(draft.get("question"), dict):
        raise ValueError("Saved question required")
    if not isinstance(trusted_passages, list) or not trusted_passages:
        raise ValueError("Indexed passages required")
    item = _complete_nonclinical_schema_fields(deepcopy(draft["question"]))
    # Allow only text changes; answer-key changes require a separate, explicitly
    # evidence-verified workflow. Original drafts remain immutable.
    if question_edits is not None:
        if not isinstance(question_edits, dict) or not question_edits or set(question_edits) - {"stem", "options", "concept_card"}:
            raise ValueError("Unsupported question edits")
        if "concept_card" in question_edits:
            edits = question_edits["concept_card"]
            if (not isinstance(edits, dict) or set(edits) != {"relevance"}
                    or not isinstance(edits["relevance"], str) or not edits["relevance"].strip()
                    or len(edits["relevance"]) > 2000 or not isinstance(item.get("concept_card"), dict)):
                raise ValueError("Only a bounded concept relevance text correction is allowed")
            item["concept_card"]["relevance"] = edits["relevance"].strip()
        if "stem" in question_edits:
            stem = question_edits["stem"]
            if not isinstance(stem, str) or not stem.strip() or len(stem) > 5000:
                raise ValueError("Invalid edited stem")
            if "stem" not in item or not isinstance(item["stem"], str):
                raise ValueError("Stem field unavailable")
            item["stem"] = stem.strip()
        if "options" in question_edits:
            changes = question_edits["options"]
            existing = item.get("options")
            if not isinstance(existing, list) or not existing or not isinstance(changes, dict) or not changes:
                raise ValueError("Invalid answer edits")
            ids = {o.get("id") for o in existing if isinstance(o, dict) and isinstance(o.get("id"), str)}
            if len(ids) != len(existing) or set(changes) - ids:
                raise ValueError("Answer IDs cannot be changed")
            for option in existing:
                if option["id"] in changes:
                    value = changes[option["id"]]
                    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
                        raise ValueError("Invalid answer text")
                    if not isinstance(option.get("text"), str):
                        raise ValueError("Answer text unavailable")
                    option["text"] = value.strip()
    indexed = {p["passage_id"]:p for p in trusted_passages}
    if len(indexed) != len(trusted_passages):
        raise ValueError("Duplicate indexed passage")
    citation_excerpts = citation_excerpts or {}
    option_evidence = option_evidence or {}
    if not isinstance(citation_excerpts, dict) or not isinstance(option_evidence, dict):
        raise ValueError("Invalid revision evidence")
    citations = item.get("evidence")
    if not isinstance(citations, list):
        raise ValueError("Question citations required")
    for raw_index, excerpt in citation_excerpts.items():
        # JSON object keys are strings; accept canonical decimal indices only.
        if type(raw_index) is int:
            index = raw_index
        elif isinstance(raw_index, str) and raw_index.isascii() and raw_index.isdecimal() and (raw_index == "0" or not raw_index.startswith("0")):
            index = int(raw_index)
        else:
            raise ValueError("Invalid citation correction")
        if index < 0 or index >= len(citations) or not isinstance(excerpt, str) or not excerpt.strip():
            raise ValueError("Invalid citation correction")
        citation = citations[index]
        if not isinstance(citation, dict):
            raise ValueError("Invalid citation entry")
        source = indexed.get(citation.get("passage_id"))
        if source is None or citation.get("textbook_id") != source.get("textbook_id"):
            raise ValueError("Citation not in indexed textbook")
        from item_source_reconciliation_v2 import _format_normalized
        if _format_normalized(excerpt) not in _format_normalized(source["excerpt"]):
            raise ValueError("Citation correction must match indexed text")
        citation["excerpt"] = excerpt
    if option_evidence:
        opts = item.get("options")
        keys = item.get("key")
        if not isinstance(opts, list) or not isinstance(keys, list):
            raise ValueError("Answer choices required")
        ids = {o["id"] for o in opts if isinstance(o, dict) and isinstance(o.get("id"), str)}
        if set(option_evidence) != ids:
            raise ValueError("Every option requires an evidence explanation")
        for option_id, entry in option_evidence.items():
            if not isinstance(entry, dict) or set(entry) != {"verdict", "passage_ids", "explanation"}:
                raise ValueError("Invalid option evidence")
            expected = "supports_key" if option_id in keys else "refutes_distractor"
            if entry["verdict"] != expected or not isinstance(entry["passage_ids"], list) or not entry["passage_ids"] or any(pid not in indexed for pid in entry["passage_ids"]) or not isinstance(entry["explanation"], str) or not entry["explanation"].strip():
                raise ValueError("Option evidence incomplete or unindexed")
        item["distractor_evidence"] = deepcopy(option_evidence)
    issues = validate_complete_item(item)
    issues.extend(reconcile(item, trusted_passages))
    issues.extend(check_answers(item, trusted_passages) if item.get("format") in ("MC", "MS") else check_special(item, trusted_passages))
    return {"parent_draft_id":draft.get("draft_id"), "question":item,
            "issues":issues, "requires_human_source_verification":True,
            "requires_clinical_review":True, "can_publish":False,
            "saved":False, "database_writes":False, "generation_performed":False}
