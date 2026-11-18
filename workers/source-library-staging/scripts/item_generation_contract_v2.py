"""Strict v2.0 generation contract, separate from legacy question generation.

Section 18 requires separate concept-card, item-draft and rationale calls.
This module builds requests only: no network, credentials, database or paid AI calls.
"""
from item_standard_v2 import check as schema_check

RULES_VERSION = "2.0"
FORMATS = ("MC", "MS", "SA", "DD", "HS")
STEPS = ("concept_card", "item_draft", "rationale")


def build_step(step, *, mode, domain, section, objective, evidence, format=None,
               concept_card=None, draft=None, topic=None, choice_plan=None):
    if step not in STEPS:
        raise ValueError("Unknown generation step")
    if topic is not None and (not isinstance(topic, str) or not topic.strip() or len(topic) > 500):
        raise ValueError("Invalid selected topic")
    if mode not in ("NCE", "SEE") or domain not in ("I", "II", "III", "IV"):
        raise ValueError("Invalid exam mode/domain")
    if not isinstance(section, str) or not section.strip() or not isinstance(objective, str) or not objective.strip():
        raise ValueError("Section and objective required")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("Indexed evidence required")
    for passage in evidence:
        if not isinstance(passage, dict) or not all(passage.get(k) for k in ("passage_id", "textbook_id", "excerpt")):
            raise ValueError("Each source requires passage ID, textbook ID and excerpt")
    if step in ("item_draft", "rationale") and format not in FORMATS:
        raise ValueError("One of five v2.0 formats required")
    if step in ("item_draft", "rationale") and not isinstance(concept_card, dict):
        raise ValueError("Concept card required before drafting")
    if step == "rationale" and not isinstance(draft, dict):
        raise ValueError("Draft required before rationale")
    instructions = {
        "concept_card": "Return one FLAT JSON object, not a nested concept_card wrapper. Required keys: objective (string EXACTLY matching the input objective code), mechanism (nonempty string), relevance (nonempty string), misconception (nonempty string), counterfactual (nonempty string), evidence_ids (nonempty array of UNIQUE passage_id strings copied verbatim from supplied evidence). Do not use textbook_id, page number, citation label, or invented IDs in evidence_ids. Ground all clinical claims in the supplied passages. If the excerpt only classifies agents, mechanism must describe that classification; do not add receptor physiology from memory. In multi-column text, only explicit table entries establish category membership; nearby treatment prose does not join a category automatically. Present a misconception as a potential incorrect inference without inventing its prevalence. Plan the case before drafting: state a source-supported original condition and a different source-supported condition that changes the correct response. Use paired components only when the concept needs both. Put the exact original and replacement condition phrases in counterfactual. The draft must use those phrases, preserve this comparison, and include both responses among its parallel choices. Relevance must state only the direct clinical importance of the supplied mechanism; do not invent inventory, stocking, regulatory or workflow requirements. A source describing where rescue treatment must be stocked does not prohibit stocking triggering drugs. Do not add markdown.",
        "item_draft": "Return exactly one FLAT JSON object (no draft/item wrapper). Include format EXACTLY equal to the requested two-letter format (MC, MS, SA, DD, HS), and a nonempty string stem. Use clinical application or analysis when appropriate; do not invent citations or unsupported facts. Assess the selected mechanism directly; do not drift to related interventions. For MC: options must be an array of exactly four objects with id A, B, C, D, nonempty text and error_pattern (null for keyed answers, a specific learner error for distractors); key must be an array containing exactly one correct option ID; select_count must be null. For MS: four to six such sequential options, key an array of exactly two or three correct IDs, select_count equal to that number, and stem must contain (Select 2.) or (Select 3.). For SA: numeric sa.answer, sa.tolerance, sa.unit, sa.rounding, sa.worked_solution, with no choices. For DD: dd.left and dd.right must each contain exactly four objects with nonempty unique id and text; use a distinct visible label for each entry. dd.pairs must map every left id to exactly one existing right id, using each right id once. Set options to an empty array; matching is not multiple choice. For HS: only a genuinely licensed figure with license, correct_region and two near_miss_regions; never invent a license. Include reasoning_level (recall, application or analysis), population (adult, pediatric, obstetric, geriatric, obese, SUD, immune or null), crisis_scenario (boolean), evidence (array of source objects with textbook_id, passage_id and pdf_page drawn only from supplied passages), and fields model, distractor_evidence, TOP-LEVEL numbers_verified_against_page_image (always false in this text-only generation step), enemy_ids, self_check, audit and stats. For unused format-specific fields sa, dd, and hs use explicit null values; include ALL THREE keys even for MC/MS. Include audit as an array, self_check as an object, and stats as an object; empty containers are allowed only when not yet evaluated and must never imply approval. For each evidence citation, return an object with exactly textbook_id, passage_id, and pdf_page copied from the supplied source (use pdf_page_start as pdf_page). Omit excerpt: the trusted server attaches the exact indexed text after verifying all three source identifiers. If the passage lacks pdf_page_start, flag it for human review; do not guess a pdf_page. Return an array of OBJECTS ONLY, with no empty strings, separators, null entries, ellipses or reconstructed quotations. Include a citation for every passage ID used in distractor_evidence. A source reference is not proof that it supports a claim; each option explanation must still identify affirmative support or contradiction in that source. For MC/MS, distractor_evidence MUST be an object with exactly one entry per option ID; each entry has verdict (supports_key for the keyed option, refutes_distractor for other options), passage_ids (nonempty array of supplied passage IDs), and explanation (nonempty evidence-based text). Build the distractor_evidence map in the same item_draft response, not a later rationale call. Check that its keys exactly match the option IDs, that each passage ID exists in the supplied evidence, and that each explanation identifies affirmative support or contradiction from the source rather than silence. For a negatively worded NOT/EXCEPT stem, supports_key marks the option answering the negative question; the other verdicts must still be grounded in the passage. If the supplied passage cannot justify a choice, do not fabricate an evidence link; explicitly flag uncertainty for human review. Follow NCE/SEE Item Generation Standard v2.0 as governing authority: R-2.1 and R-2.4 require positive source evidence for the key AND evidence showing every distractor false; absence from a passage is not disproof. R-2.8 prohibits copying eight or more consecutive source words into the stem or options. R-4.3 requires each stem detail to matter; R-4.8 discourages NOT/EXCEPT. R-5.3 requires a meaningful counterfactual. R-6.1 through R-6.3 require plausible single-flaw distractors tagged by error pattern; do not use Correct or Incorrect as an error_pattern. R-6.8 requires parallel options of similar length, with the key no more than about 15 percent longer than the next-longest option. Keep options to about 6–14 words when possible, put shared context in the stem, and compare option word counts before returning the draft. R-6.9 prohibits rationale in options. Before selecting the key, perform an adversarial option-by-option test: assume EACH option could be correct, identify the clinical assumptions under which it would be true, and compare those assumptions against the exact stem. Reject or rewrite any distractor that could also satisfy the stem, including synonymous mechanisms, overlapping causes, and answers that become true when unspecified conditions are assumed. Each distractor must be false under the stated scenario, not merely less preferred. Never dismiss another true contributor as secondary or partial truth unless the supplied source explicitly establishes that hierarchy. When the source gives combined mechanisms, ask for the combination and make every option a parallel combination of the SAME TWO VARIABLES, varying only their direction or state instead of introducing other causes. The source must contradict at least one component of every incorrect combination. Do not invent a primary reason. For MS, independently verify the precise number of correct options and reject an ambiguous extra true option. When a source only supports a general mechanism but cannot resolve the scenario-specific distinction, flag uncertainty instead of forcing a unique key. R-12.9 requires duplicate concept screening. If evidence is insufficient, do not invent support or treat silence as refutation; flag for human review. Never claim human approval or verified page images. No all/none above, true/false, fill-in or select-all-that-apply.",
        "rationale": "For MC/MS, finalize the planned counterfactual against the FINISHED draft: include counterfactual_test with exactly from_text (one unique complete condition substring of the stem, at most 200 characters), to_text (a different source-supported clinical condition, at most 200 characters), and expected_key (a different existing option ID array, same selection count). Keep every other stem fact and all choices unchanged. Never replace the entire stem, a question instruction, or an answer statement. This is an author proposal; a fresh independent blind solve must verify it. Do not alter any draft field. Also return the four rationale keys: core_concept (string), why_key_wins (string), trap (string), and distractor_breakdown (object keyed by EVERY option ID, including the keyed answer(s), with string explanations). Do not wrap the object under rationale or repeat the draft, source excerpts, or evidence objects. Use one or two concise sentences per field and per option explanation. For each option, explicitly state the source-supported mechanism or classification (do not invent a mechanism when only classification is supplied), why it is correct or incorrect IN THE STEM CONTEXT, and what the supplied textbook evidence affirmatively establishes. Challenge each distractor as though it might be another correct answer; if any distractor remains defensible, identify the ambiguity for human review rather than inventing a disproof. Do not use absence from a passage as disproof. Do not invent citations. Preserve draft answer and source IDs. Leave uncertain facts flagged for human review.",
    }
    if step == "item_draft" and format == "MC":
        instructions[step] = instructions[step].replace(
            "source objects with textbook_id, passage_id and pdf_page drawn only from supplied passages",
            "source selector objects containing only passage_id drawn from supplied passages")
        start = instructions[step].index("For each evidence citation")
        end = instructions[step].index("Include a citation for every passage ID", start)
        instructions[step] = (instructions[step][:start]
            + "For evidence, return an array of objects containing ONLY passage_id copied from a supplied source. Omit excerpt, textbook_id and pdf_page: the trusted server attaches the exact indexed text and source identity from that ID. Do not add fields, fabricated IDs, ellipses or reconstructed quotations. "
            + instructions[step][end:])
    if step == "rationale" and format == "MC" and choice_plan is not None:
        # The server already bound the plan to this finished stem. Ask this call
        # only for explanations, not another version of the same clinical edit.
        instructions["rationale"] = (
            "Return exactly the four rationale keys below, with no counterfactual_test or other fields. "
            "The supplied planned counterfactual is already bound to the finished stem and must not change. "
            + "Return the four rationale keys:" + instructions["rationale"].split("Also return the four rationale keys:", 1)[1])
    # Keep the full evidence in trusted validation; send only fields the model
    # needs for grounding and source attribution. Do not truncate excerpts.
    compact_evidence = [{key: passage[key] for key in
        ("passage_id", "textbook_id", "excerpt", "pdf_page_start", "pdf_page_end")
        if key in passage} for passage in evidence]
    if step == "concept_card" and format == "MC":
        from item_source_quote_spans_v2 import prepare
        quoted, _ = prepare({"source_passages": compact_evidence})
        compact_evidence = [{**{k: v for k, v in passage.items() if k != "excerpt"},
                             "quote_spans": source["quote_spans"]}
                            for passage, source in zip(compact_evidence, quoted["source_passages"])]
    from item_board_quality_v2 import classification
    target_labels = classification(domain, section, objective)
    quality_instructions = (
        " R-8.4: omit halothane, ranitidine and bleeding-time testing from all authored text unless the stem is explicitly historical, even if an indexed source mentions them. "
        "Keep the selected topic as the assessed concept. If it requests a physiological relationship, test that relationship directly; do not substitute a nearby treatment recommendation from the excerpt. Use the supplied blueprint labels, not just a syntactically valid code. A wrong topic/objective match must be flagged. "
        "For MC/MS, label the actual reasoning level honestly: important factual recall is permitted by R-10.1; application or analysis must interpret relevant findings to reach a decision or explanation. Do not pad recall with a decorative patient. Use parallel paired-variable choices only when the concept genuinely has two relevant attributes, per R-6.7. Do not use a vague variable/depends alternative merely to reach four choices. "
        "Design the stem and all four choices around the concept-card counterfactual: changing its named clinical condition must make a different existing option correct. Wrong choices should represent plausible mistakes or a different clinical condition supported by the evidence, not unrelated or obviously unsafe actions. R-3.3/R-5.3: counterfactual must quote the exact original condition and its replacement, name a variable actually used in the stem, state its changed value or condition, and say how the correct response changes. Include the complete changed condition and its diagnostic qualifiers in that exact phrase; the changed stem must not retain a contradictory parenthetical diagnosis or label. A restated fact, swapped answer option or unrelated hypothetical is insufficient. "
        "The original case contains ONE current clinical condition; the counterfactual is a separate hypothetical, never the question itself. Do not describe a patient changing from one chronic disease into another, and do not place both original and replacement conditions in the original stem. Never give away the expected response in a parenthetical label. When the selected topic names contrasting physiological components and the sources explain both, assess their combined response using the same two components in EVERY choice; choosing one topic branch for a single direction lookup does not meet the requested comparison. Establish one plausible original condition, then privately test replacing that entire condition with the alternative while all unrelated facts stay fixed. Quote only those condition phrases in the counterfactual, not answer statements or compliance directions. "
        "The final stem must stand alone without asking what was described in a source, passage or textbook. For application or analysis, make a clinical finding change a decision or interpretation; avoid decorative patient details. Do not add age, sex, numerical vitals, doses or thresholds that the task does not need. For MC/MS omit equations, calculations and formula definitions from concept cards and explanations when the original page image is unverified; interleaved PDF columns can reverse numerator and denominator. This text-only generation cannot certify a dose, equation or threshold against its original page image. "
        "R-9: start the trap with the specific incorrect option ID (for example, Option C), then name the most plausible distractor and the specific mistaken reasoning that would make a learner select it under this stem. Check that this reasoning actually leads to that wrong selection. "
        "Explain the clinical principle directly and concisely, rather than repeatedly saying 'the passage says' or 'in this stem context'. "
        "Set keyed options' error_pattern to null. Tag each distractor with the specific learner error, not merely its drug class or whether it is correct. "
        "Do not claim a self-check passed; the server records observed screening results."
    )
    if step == "concept_card" and format == "MC":
        # R-6.7 recommends crossed pairs when a concept has two attributes;
        # it does not require two physiological measurements for every MC item.
        instructions[step] = (
            "Return one flat concept-card JSON object with objective copied exactly, mechanism, relevance, "
            "misconception, counterfactual, evidence_ids, and choice_plan. Use only supplied indexed excerpts. "
            "Test one important concept in the selected topic and objective. Choose recall, application or analysis "
            "as the evidence and task warrant; do not dress recall in a decorative patient scenario. "
            "A clinical application should interpret relevant findings to reach one decision or explanation. "
            "Use ordinary homogeneous single-best-answer choices by default. Use crossed paired responses only "
            "when the assessed concept actually has two source-supported attributes (R-6.7), never to force an unrelated second task. "
            "choice_plan contains response_variables (one clinical response/category, or two related clinical components), "
            "stem_condition and alternate_condition (different complete phrases, each at most 200 characters), lead_in (one shared question ending in ?, at most 200 characters), "
            "key and alternate_key (different single-ID arrays), four options A-D each with id and states, and option_grounding. "
            "First choose the narrowest distinction the passages explicitly resolve for two contrasting cases. "
            "If the evidence classifies a local unit, component, or compartment, ask for its classification and use four peer classifications at that level. Do not substitute whole-patient outcomes or whole-system behavior for local responses. "
            "If the evidence gives a measurement or function, use four comparable measurements or functions at the same observation point. If there are too few plausible, source-resolved peers, choose a different distinction within the objective. "
            "In an equipment fault, several responses can occur together. Prefer a named indicator, control, or observation point with a specified triggering condition. Avoid asking which response occurs first unless the passage establishes the sequence and the case gives the relevant settings and gas flows. "
            "Separate an instrument's direct input from downstream changes it could observe as a consequence. Source support for the first relationship does not establish that the consequential observation cannot occur. "
            "Before locking the plan, read the choices without the case: discard any conspicuous throwaway, any uniquely technical or qualified answer, and any option that could be rejected on wording alone. "
            "Build option_grounding BEFORE committing to choices: an object keyed by exactly A, B, C, D. Each entry has exactly passage_id (a supplied ID), span_ids (one to three unique quote_spans IDs belonging to that passage, such as [\"q0\"]), and explanation (one or two original sentences, at most 700 characters). For the original case, explain why this option answers the question or why it is false, using what the selected spans affirmatively establish. Choose an excerpt that actually resolves that option under the stated condition; source silence is not refutation. A citation or selected span alone never proves a claim. Do not transcribe source text; select its span IDs. For each distractor, identify the case fact that excludes it and the affirmative source fact that makes that exclusion valid. If the excerpt describes a different classification, explain the distinguishing criterion rather than arguing that the option is missing from a list. For equipment, distinguish what a monitor directly measures from broader properties someone might infer. Omit claims about the whole system from a passage that describes one measurement. The server locks these explanations into distractor_evidence and rationale; later calls cannot embellish them. If no excerpt supports the distinction, choose a different evidence-supported distinction within the requested topic; do not invent support. "
            "For receptor-level questions, all four choices must describe competing actions at the SAME receptor level, rather than mixing presynaptic release, receptor action and muscle contractility. For any narrow task, apply that same level of specificity to EVERY option; category membership must not reveal the key without the case. "
            "Each states array has exactly one value per response_variable, in that order. All four alternatives must differ. "
            "Keep each component label to a few words, each state at most 80 characters, and each complete rendered option at most 180 characters. "
            "For one component, each state becomes the complete ordinary option text, with no label prefix. "
            "Each option states only the requested answer, never an answer plus its explanation. Do not use because, thereby or so that. "
            "All options must answer the same lead-in and belong to the same clinical category; do not mix quality, onset and mechanism as alternatives. Keep shared drug, device, patient and exposure context in the stem. When the question asks for a mechanism, offer competing mechanisms under that SAME context; do not make the keyed option the only one naming the case drug while distractors name unrelated drugs, populations or procedures. True trivia about a different agent is not a plausible competing explanation of this case. "
            "For two components, the server renders parallel labelled pairs. Return id and states only, not text or error_pattern. "
            "Choose a response that actually changes with the clinical or device condition. Do not force a counterfactual onto an invariant ranking such as the most reliable indicator or an always-false factual explanation. A change in case findings cannot reverse an instrument-reliability fact. If the topic includes an invariant fact, assess its source-supported condition-dependent mechanism or consequences instead. Both the keyed and alternate-key options must be entirely true in their own planned cases, not partly correct answers containing a false justification. "
            "Commit to the exact shared lead_in while planning both cases, not in the later drafting call. It must ask the SAME precise source-supported task, affected compartment, measured variable and timing in both cases. A different diagnosis can retain the same mechanism for a shared global outcome; do not assume changing the diagnosis changes the answer. Test each complete case plus this exact lead-in against ALL four choices. The original case must have one source-supported key and a meaningful change "
            "to its clinical condition must make a different existing choice correct. Evidence must affirm the correct response "
            "and refute every distractor under each case, rather than rely on silence or an invented primary/secondary ranking. "
            "For paired responses, trace determinants of both components; an unchanged determinant cannot cancel a changed shared determinant. "
            "Describe causes/events and necessary qualifiers without putting the expected answer in the condition. "
            "For increased/decreased responses, state the comparison baseline explicitly and keep it fixed under the changed case. "
            "Absence of an adverse condition does not establish excellent efficacy, normality or safety; require affirmative support. "
            "Put every condition-dependent finding inside its complete replaceable condition phrase, not elsewhere in the draft. "
            "The original stem must contain only its original case. Quote the exact original and alternate phrases in counterfactual "
            "and identify the changed response. Explain the supported mechanism concisely. Relevance states its direct clinical importance "
            "without unsupported treatment, regulatory or workflow requirements. Misconception is a plausible false inference "
            "refuted by the evidence, without invented prevalence claims. evidence_ids are exact supplied passage IDs. "
            "Do not add equations or quantitative claims that require original-page image verification. Never claim approval.")
        quality_instructions = ""
    if step == "concept_card":
        quality_instructions += (
            " Write every planned clinical condition and response state in original wording. R-2.8 prohibits eight consecutive source words in the eventual stem or options, including text inserted verbatim from a choice_plan. "
            "Paraphrase source facts before locking stem_condition, alternate_condition and planned option text; do not use a textbook sentence as a case template.")
    if choice_plan is not None:
        quality_instructions += (
            " Use the supplied private choice_plan. Copy key and all planned option id/text fields EXACTLY. "
            "Omit states from final options; supply error_pattern as null ONLY for the original key and a specific learner "
            "error for EACH of the other three options, including the option correct under the separate alternative case. "
            "The alternate case is not the original question. For item_draft, return stem exactly as {{STEM_CONDITION}} {{LEAD_IN}}. The server inserts the authored case and shared question verbatim. Do not add or revise context, findings or the lead-in. For rationale, use the already rendered draft. "
            "Do not return a new counterfactual in the rationale: the server preserves the exact planned stem edit. "
            "Source and independent blind checks will still test the plan; never assert approval.")
    if format == "MC" and choice_plan is not None:
        if step == "item_draft":
            instructions[step] = instructions[step].replace("fields model, distractor_evidence, TOP-LEVEL", "fields model, TOP-LEVEL")
            start = instructions[step].index("For MC/MS, distractor_evidence MUST")
            end = instructions[step].index("Follow NCE/SEE Item Generation Standard", start)
            instructions[step] = (instructions[step][:start]
                + "The server supplies distractor_evidence from the locked option_grounding; omit distractor_evidence from this response. "
                + instructions[step][end:])
            quality_instructions += " Omit distractor_evidence: the server attaches the locked option_grounding map. Do not author new option explanations. Cite every option_grounding passage_id in evidence."
        elif step == "rationale":
            instructions[step] = (
                "Return exactly core_concept, why_key_wins and trap as concise strings. Omit distractor_breakdown: the server attaches the locked option_grounding explanations for all four options. "
                "Explain only the supported distinction already established in option_grounding. Do not add new device behaviors, receptor mechanisms, alarm behavior, exclusions or absolute claims absent from the supplied excerpts. "
                "Start trap with the specific incorrect option ID and the learner error that would lead to it. Do not return a counterfactual or modify any draft field. "
                "The planned span references are author-selected evidence, not a clinical pass; independent checks and human review remain required.")
    return {"rules_version": RULES_VERSION, "step": step,
            **({"choice_plan": choice_plan} if choice_plan is not None else {}),
            **({"topic": topic} if topic is not None else {}),
            "mode": mode, "domain": domain, "section": section, "objective": objective,
            "blueprint_labels": target_labels,
            "format": format, "evidence": compact_evidence, "concept_card": concept_card,
            "draft": draft, "instructions": ("Focus on the selected topic, using only the supplied evidence for clinical claims. " if topic is not None else "") + instructions[step] + quality_instructions,
            "required_output": ("concept_card" if step == "concept_card"
                                else "draft" if step == "item_draft" else "rationale"),
            "human_review_required": True, "auto_publish": False}


def validate_complete_item(item):
    if not isinstance(item, dict) or item.get("rules_version") != RULES_VERSION:
        return [{"rule_id": "R-15", "message": "Expected complete v2.0 item"}]
    return schema_check(item)
