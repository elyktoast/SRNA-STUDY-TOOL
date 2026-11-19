# MC generator acceptance — 17 November 2026

Latest runtime work: [18 November reliability record](mc-runtime-reliability-2026-11-18.md). The two passing drafts remain pending clinical review; no new quality acceptance is claimed before live verification.

Scope: staging MC generation only. MS, SA, DD and HS development is paused. No clinical approval, bank publication or production promotion has been performed.

## Fixed finish line

A usable MC draft generator must handle lecture-derived and freeform requests, retrieve trusted textbook evidence, produce a single best answer with supported distractor explanations, complete all ten automated checks, save/recover an unpublished draft and pass current-index revalidation. Human clinical review remains required. A varied acceptance set is required; a single success is insufficient.

## Completed work — do not repeat

- Canonical semantic index: 9,000/9,000 items, including positive-duplicate and unrelated negative live controls. Reuse it; do not reembed/rebuild the existing bank.
- Seven trusted generation textbooks. The OR guide remains held for provenance. PDF page locations are not verified printed-page citations; numeric/page-image certification remains outside this text-only MC milestone.
- One complete pharmacology MC, including actual UI current-index revalidation with zero issues.
- Durable unpublished saves and completed-only recovery. Incomplete/flagged reviews block single and bulk approval.
- Complete MC rewrite responses: the prior 3,500-token output limit caused truncation. Two subsequent live requests returned complete rewrites with the bounded 6,144-token ceiling.
- Cue-response JSON handling: subsequent live runs completed all five trials. A completed cue test can still correctly flag answer cues.
- Specific lecture objectives precede broad headings. The visible objective selector agrees with the classified request.
- Clinical lecture search normalization is shared by evidence preflight and final independent MC option retrieval. It removes the teaching prefix, retains the entire clinical relation and preserves owner/book scope. The live varied-topic request no longer reported missing option-search matches.

## Acceptance ledger

| Sample | Draft ID | Automated result | Current disposition |
| --- | --- | --- | --- |
| Local anesthetic ionization/onset | `8da6a89a-26b3-44dd-ad42-a70405dc6e23` | 10/10; zero rewrites; current-index revalidation has zero issues | Unpublished, ready for clinical review |
| Absorbent exhaustion, initial | `71238ca0-21ed-481d-bd88-eb0a519796df` | 7/10; citation transcription consumed repair; ambiguous options/rationales remained | Held; no second rewrite |
| Absorbent exhaustion, trusted citation selectors | `e05468e2-1eab-4cec-9efd-79180852f04a` | 5/10; citation transport fixed; substantive counterfactual, wording and explanation issues remained | Held; no second rewrite |
| Lecture FRC, before completion fix | `0465c585-a7f4-4d73-b73c-69973ace53c8` | 6/10; repair truncated, cue JSON incomplete | Held; no second rewrite |
| Lecture FRC, completed missing review | `65c2e793-a7af-4746-bfb6-1abf9993085c` | 10/10; current-source revalidation has zero issues | Unchanged question, still one rewrite; ready for human clinical review |
| Neuromuscular lecture, shared question plan | `92b781bd-a3cc-4024-a48c-e01ea135102e` | 8/10; revised case and all explanatory evidence passed; cue reviewer guessed key 5/5 | Held; independent option adjudication remains blocked by cue failure |
| Freeform oxygen pressure failure control | `41c206d6-2520-437c-b626-7f8f8887b304` | 8/10; one complete repair; source review rejected unsupported distractor explanations | Held; no second rewrite |
| Different lecture: shunt/dead space | `d15912da-15a5-4058-9aad-218993c2076f` | 7/10; searches completed; counterfactual and cue checks flagged after one repair | Held; no second rewrite |

The shunt sample changed the case to pulmonary embolism but retained a lead-in about the overall cause of hypoxemia. The blind changed-stem solver still selected the original answer. This is an observed task-scope failure, not a request to weaken the counterfactual rule. The repair previously received only a generic failure message. A targeted correction now carries its exact validated stem edit, expected answer IDs and independently selected IDs into the single repair; it includes no raw reviewer output and does not expose the key to the blind reviewer. Tests verify feedback propagation, isolation, one repair and continued failure/pending behavior.

## Staging changes and validation

- PR #212: `0bce0f7027775af14d2e69556f623d2329534a38`; complete bounded repair/cue responses and visible objective handoff. CI 44115129494 passed. Cloudflare build 38b3bceb-3528-4654-9f05-77dd8e0a07db succeeded.
- PR #213: `2f199a05f4a0f615647f16a675dde470f2b22c0b`; shared clinical query for independent MC option retrieval. CI 44118482170 passed. Cloudflare build 587b7e8b-db7f-431a-8910-3fba49800620 succeeded; container image afc1758701ffb17e16611f8b1a8184cb92ec120c2c0739a4a32fb4d4c6c9842c settled before the next paid request.
- Current planning/repair batch: 1,055 Python tests succeeded (four skipped), 200 Node checks passed and repository validation passed. Live acceptance of the new planning contract is still required.

## Remaining work

1. Continue varied new-question quality validation; the shared-lead-in contract and saved-review completion now have live verification.
2. Complete varied-topic MC acceptance; distinguish retrieval/transport failures from clinical or writing failures.
3. Require zero current-index issues for every accepted sample. Keep failed drafts blocked and never give them a second automatic rewrite.
4. Present only genuinely passing drafts for the required human clinical pilot before scaling. Do not call the near-autonomous quality goal complete on the strength of unit tests or one passing question.

Known limits: automatic classification can hold unfamiliar wording; selecting the respiratory objective allowed the new lecture test to proceed. Actual personal lecture-file upload in the browser has not been exercised; pasted objectives were tested in the live UI and PDF/PPTX fixture planning separately. Global manual replay of partial checkpoints still needs durable rewrite-budget hardening; the supported UI uses fresh item IDs and completed-only recovery.

## Complete question planning, not a later free-form lead-in

The existing private MC plan committed to case conditions and choice text but omitted the actual question. A later authoring call could independently introduce a lead-in whose task did not yield the planned alternate key. The plan now requires one bounded `lead_in`, assessed against both complete cases. Drafting returns only the two stem placeholders; the server inserts the authored case and question verbatim and rejects any different lead-in or added context. Rendering does not claim clinical truth. Final source, blind, changed-case and cue checks remain mandatory. Older incomplete private plans without this field fail closed rather than invent a missing question; completed saved drafts remain reviewable.

Regressions cover missing/malformed questions, embedded case text, exact two-slot rendering, draft-task drift, added clinical context, checkpoint retention and preserved private-plan removal from the canonical item. Counterfactual mismatch feedback now also carries the exact tested edit and expected/observed IDs to the sole repair.

The completed equipment control independently confirmed that source review can reject unsupported explanations even when eight other checks pass. In particular, the source did not establish the authored claim that a supply-pressure alarm would not trigger on complete pressure loss. The source gate remains unchanged. This is a failed clinical/source quality sample, not an infrastructure failure and not acceptance.

## Deployed shared-question result

PR #214 merged as `da23755d8c02a4bb4f5054a96bb74a2e2d7c2d8c`; CI 44162064440 succeeded. Cloudflare build `a97b20b0-1b7b-4726-b5b5-0d65948a7ae2` succeeded. Container image `b483d0adc4b69a41c33052e8c6a6355251a2482bba0746ca6e34ba4237b837dd` settled before the next paid request.

The new neuromuscular lecture request completed planning, exact stem rendering and rationale generation, used one complete repair and saved draft `92b781bd-a3cc-4024-a48c-e01ea135102e`. The changed-case solver independently chose B as expected, explanatory source support passed, and eight checks passed overall. Options-only review correctly held the draft after identifying the keyed option in all five shuffled trials. Its other choices included presynaptic/contractile mechanisms outside the requested receptor-level category. No gate was relaxed and no second rewrite was performed. This verifies the shared question contract in a live pipeline; it does not establish broad MC quality acceptance.

The fresh FRC request stopped before a draft was saved with DRAFT_VALIDATION. Its private plan was retained, and no automatic repair or clinical approval was performed. The failed fresh candidate does not verify or invalidate the earlier saved nine-of-ten question; it is a separate planning/draft failure.

## Complete a missing review on the unchanged saved MC

The new staging-only Complete missing option review action is restricted to an unchanged, unreviewed MC draft whose other nine automated stages already pass. It refuses flagged stages, missing/stale duplicate-index receipts, completed clinical judgments, saved revisions, missing consent and stale versions before requesting a review. It searches the current owned, ready books represented in the saved evidence, then invokes the existing distinct blind option reviewer and existing verbatim-quote adjudicator. No authoring, question rewrite, clinical approval or publication is permitted.

A per-draft transaction advisory lock prevents concurrent paid reviews. Saving uses compare-and-swap checks on the full original question, screening report and update time, rejects concurrent revisions, and verifies the independently retrieved source snapshots still match the index. The stored receipt binds the result to the question/source hashes and original author/reviewer model identities. A completed uncertain or invalid-quote judgment remains blocked and cannot be repeatedly sampled for a better grade. Provider-only incompletion can remain pending.

The action refreshes the clinical editor and keeps human review pending. The gateway enforces authenticated POST and rejects any response claiming question modification, generation, rewriting, publication or clinical approval. The MC planning fingerprint is also versioned for the shared-question contract, and safe validation detail codes reach the admin status without exposing provider text.

Validation: 1,066 Python tests succeeded (four skipped), 203 Node checks passed, repository validation passed. Live completion of the existing nine-of-ten draft remains to be tested after deployment. The near-autonomous quality milestone is still open; these checks are not a claim that varied new questions consistently pass.


## Verified milestone: lecture and freeform MC workflows

[Acceptance run 44173067107](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44173067107) succeeded against deployed staging commit `9c8089cb5eee12fbac12f492670bf1827b9a2efe` (PR #215; CI 44169325269 passed). Its exact Cloudflare build was `409749dd-864f-40a6-8389-e0884d20bcdc`; the deployed image was `6ab6d19131ab05bc64d6444c075ebd28940072a569f192e20b6a7fabffb44b16`.

The original FRC lecture draft `65c2e793-a7af-4746-bfb6-1abf9993085c` now passes all ten automated stages. Its authenticated current-index revalidation returned zero issues, no generation, no database writes and unpublished status. The review-completion action itself wrote only its screening result and receipt. It made no authoring call, performed no rewrite and did not modify the saved question. The original rewrite count remains one. Question SHA-256 before/after: `fb501022535deea529decdc3b25afc1d0908af900d1c6bee467ac1e4a6d10e58`. The independently queried stored-question checksum also remained unchanged.

Together with the previously verified freeform local-anesthetic question `8da6a89a-26b3-44dd-ad42-a70405dc6e23`, there are now two unpublished MC drafts from different workflows/objectives with all automated checks passing. Both remain pending human clinical review; neither has been approved or published.

The browser connection became unavailable before the paid completion action was clicked. The authenticated staging runner completed that action instead. Its first two attempts stopped before any paid review because of deployment-metadata checks: a preview build overwrote the same-commit GitHub check, and the CI credential lacked deployment-read access. The successful run used a fresh, five-minute connected-service deployment verification, pinned to the exact successful build, code and image. No CI permissions were expanded. The review-only runner, its three offline safety checks and its exact deployment verification are retained on branch `verify/mc-saved-option-review-20261117`.

**The MC workflow is now demonstrably operational in staging for supervised review. Consistent near-autonomous quality across new topics is not yet established.** The cue/source failures in the other samples remain blocked, and all other question formats remain paused. The next work is broader MC quality validation and the required human clinical pilot, not reindexing the completed bank or rebuilding the finished workflow.


## Next quality batch: source-first option explanations

The observed neuromuscular cue failure mixed receptor-level alternatives with presynaptic and contractile mechanisms. The equipment source failure introduced unsupported alarm behavior while explaining a distractor. This batch narrows the requested answer category and moves per-option explanation authoring into the private MC choice plan, before drafting.

Each option must select one supplied passage and one to three existing quote-span IDs, with a bounded explanation of why it is correct or false in the original case. The server validates span membership before any drafting call or checkpoint write; it does not infer support from a real span. It carries the locked explanations into both `distractor_evidence` and `rationale.distractor_breakdown`, rejecting later disagreement. The distinct independent source reviewer still assesses clinical support using the full trusted excerpts. Cue, changed-case, duplicate, explanation, approval and one-rewrite gates are unchanged. Completed saved drafts are unaffected; incomplete older plans fail closed. The authoring/checkpoint fingerprint is v22.

Offline validation: 1,069 Python tests ran, four skipped; 203 Node checks passed; repository validation passed. These results establish implementation behavior, not acceptance of new clinical questions.

Fixed live set for this batch (one fresh request per topic, no rerolling or second repair):

| Sample | Workflow | Purpose | Result |
| --- | --- | --- | --- |
| Neuromuscular receptor action | Lecture objective | Same-level mechanisms; observed cue failure | Not run yet |
| Oxygen supply pressure failure | Freeform | Source-supported device distinctions; observed unsupported explanation | Not run yet |
| Shunt versus dead-space physiology | Lecture objective | Different mechanisms under a shared precise question | Not run yet |

The two previously passing drafts remain unpublished and pending human clinical review. No bank indexing, other-format development, production deployment or main/PR #189 merge is included.


### Live result of the first source-first batch: 0/3 accepted

Run [44194077251](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44194077251) completed against staging application commit `a0eb858dd34f08dd0445d1fd96ddfcdb447c85d3`, build `6fc72edc-9ceb-4ffa-aa1a-206609133680`, container image `535982fe6236cd4d83696b690f43e965d11e3f2be7aeda7ff8164f9f6ff65cad`. Workflow completion means results were collected; it is not clinical acceptance.

| Topic | Request item ID | Saved draft | Blocker |
| --- | --- | --- | --- |
| Neuromuscular receptor action | `2f7d0b98-e9bc-4441-86a4-747d7268c63e` | None | `CONCEPT_CARD_VALIDATION / PLAN_FIELDS` |
| Oxygen supply pressure failure | `a45703db-31ca-4e58-bb5d-11b6fc3208a6` | None | `NO_INDEXED_EVIDENCE`; no authoring call |
| Shunt versus dead-space physiology | `e23bb6fc-adb1-4283-8110-7db849f57605` | None | `CONCEPT_CARD_VALIDATION / PLAN_FIELDS` |

The implementation missed the gateway's constrained response schema: it still prohibited `option_grounding`, while Python required it. This is a product regression, not poor clinical authoring. The correction adds the source-first fields and source/span enums to the gateway schema and omits later rationale breakdown authoring for grounded plans. A regression compares the gateway's required plan fields directly with the Python validator; it also checks the actual GLM planning and rationale requests. The authoring/checkpoint fingerprint is v23. Validation: 1,069 Python tests ran (four skipped), 204 Node checks passed, repository validation passed.

The equipment harness also used an arbitrary first book and an overconstrained search string. A read-only count found zero Equipment passages for the full sentence, versus 84 for `Oxygen pressure failure`. The next bounded equipment control uses the Equipment textbook as primary and that clinical concept title. This does not fix unrestricted natural-language search; overly conjunctive freeform searches remain a known limitation. No reindexing is needed.

The runner and exact first results are retained on `verify/mc-option-grounding-20261117`. Do not rerun that paid job. The next set uses fresh request IDs after the demonstrated schema correction, with the same three clinical targets. No completed clinical judgment is being resampled and no failed draft is repaired a second time.


### Corrected-schema live set: still 0/3 accepted

Run [44195586659](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44195586659) used staging application commit `14f0e0799dc1d1d9cbe540df9b1a1f9620efc629` (CI [44195059494](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44195059494) passed). Actual successful build: `8417b976-2a7c-4ddd-8609-0b1ccad46559`; settled container image: `cda921d628f0334ac033113e297a58f52fbd972f5f1727769ec1c8c422288e8c`.

| Topic | Request item ID | Saved draft | Actual result/blocker |
| --- | --- | --- | --- |
| Neuromuscular receptor action | `afda08fb-1c15-4142-b987-39b84c2b9d92` | None | `CONCEPT_CARD_VALIDATION / PLAN_GIVEN_RESPONSE`; plan blocked before drafting |
| Oxygen pressure failure | `8881f83d-42c3-4f35-95b5-84619a906657` | None | Source-first plan validated and draft checkpoint persisted; client reported `fetch failed` after about five minutes; no completed result or saved draft |
| Shunt versus dead-space physiology | `05c89209-3ca5-42fe-b172-adf4d7d648df` | None | HTTP 500; Worker logs identify a non-JSON upstream backend 500, without a safe diagnostic rule |

A direct read-only draft query confirmed that none of these request IDs had a saved draft. The run's green status means the failure ledger was collected, not that any candidate passed. No new automated acceptance is claimed.

Connected runtime logs show successful equipment concept, draft and rationale authoring, independent review calls, two explicit Groq 429 responses with bounded waits, and one completed rewrite. **Do not manually resume the equipment partial checkpoint:** that rewrite was already spent even though the older partial checkpoint does not durably record its budget. The supported UI's fresh-item and completed-only recovery boundaries remain necessary. No second rewrite or completed-judgment resampling was performed.

The subsequent respiratory authoring calls also returned HTTP 200 from the model, but the backend ultimately returned a non-JSON 500. Its root cause is not established. Do not label it a clinical quality failure or claim that a timeout fix has been verified. The equipment disconnect occurred at approximately the common Node fetch header deadline, but the client cause code was not captured; that is a hypothesis, not a diagnosis.

The acceptance harness continued to the next topic after the ambiguous equipment disconnect, so backend work could have overlapped despite sequential client calls. The retained runner now stops the entire set after an ambiguous transport/server failure, records remaining topics as not run, and captures a fixed transport cause code without printing provider output. Three offline runner checks verify single requests, clinical holds, stop-after-disconnect/500 behavior and replay prevention. This reporting/safety correction has not been used for another paid run.

**Current outcome:** the source-first contract is implemented, schema-aligned and live-verified through equipment drafting, but it has yielded no newly accepted questions. The two previously passing unpublished drafts remain the only passing MC examples. Near-autonomous quality remains open, with plan leakage, runtime reliability/latency, and varied clinical acceptance still unresolved. No more paid samples were launched after this diagnosis.

Next work should diagnose the non-JSON backend failure and five-minute client disconnect using bounded read-only diagnostics, harden durable rewrite-budget accounting before any partial replay, and obtain a safe failed-plan diagnostic for `PLAN_GIVEN_RESPONSE` without relaxing that gate. Then run a bounded fixed acceptance set against a demonstrated correction. Keep all other formats paused, retain the complete duplicate index, and preserve both passing drafts for human clinical review.


## 18 November runtime result and next clinical control

See the [runtime reliability record](mc-runtime-reliability-2026-11-18.md). The two formerly failing runtime paths now complete and save; the ledger protects interrupted rewrite budgets and the live container peaked near 372 MiB. Both new drafts remain blocked (7/10 and 8/10), with zero new accepted questions. The apparent respiratory 8/10 was actually a generic objective-heading routing failure that produced simulation content; it is not respiratory quality acceptance.

A targeted parser correction now excludes the generic Markdown objective heading and preserves its clinical bullet. The next bounded control must prove the exact intended topic in a read-only plan before spending on one fresh clinical MC. Do not rerun or regrade either saved failed draft.

### Correctly routed respiratory control

The [18 November record](mc-runtime-reliability-2026-11-18.md) includes the exact deployment and [live run 44291780922](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44291780922). A zero-paid-call assertion verified the exact clinical lecture topic before one new request. Draft `5b7dfe6e-bcfd-4d7c-96a1-f5f30d68daba` was correctly routed and saved, but remains held at 6/10 after one repair: R-12.2 cues, R-5.3 regional/systemic task mismatch, and R-2.4 D-explanation support. Independent option review correctly stays pending. No second rewrite or judgment resampling was performed.

Runtime/admission/rewrite-budget and objective-heading corrections now have live verification. The near-autonomous MC quality milestone remains open: **zero new accepted questions**, with the original two 10/10 drafts preserved for human review. Next work is precise question/option scope and source-grounded distractor quality, not indexing or repeating completed infrastructure checks.

### November 18 source and distractor controls

Staging application `78f68d4fed158293dabbe2e02335c0783a9970bb` narrows MC planning to a single source-supported level of observation, encourages comparable alternatives, and lets the one allowed repair see up to four additional trusted passages already retrieved for the question when source support fails.

The first runner stopped during read-only preflight with a connection reset ([44390793108](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44390793108)). It made no generation request. The runner then added bounded read-only retry. The next run received `GENERATION_BUSY` during the respiratory attempt while that same item was still processing ([44391162347](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44391162347)). The receipt shows one attempt with one reserved rewrite. Result collection used completed-only recovery ([44391813241](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44391813241)).

Respiratory draft `f6440562-8a49-4293-8d67-d78e8773b811` saved at **9/10** after one rewrite. It passed the cue, editorial and explanatory-source checks that blocked the previous correctly routed respiratory item. Independent option evidence remained pending (R-12.4) after an unavailable or invalid provider response, with rate limiting observed on the option-review route. The draft also has a sentence-boundary error separating its case from its lead-in that the automated checks did not flag. Flag that wording for clinical review even if the missing automated check is completed.

Equipment draft `b34d2cdb-7acf-4831-8a27-8005476e0535` saved at **7/10** after one rewrite and completed-only recovery. It passed the deterministic wording, cue, editorial and duplicate checks. The blind solver disagreed with the key (R-12.1). The stem asked for an immediate machine response without establishing a unique sequence or all relevant gas-flow settings. The option C rationale and evidence map inferred that the downstream oxygen analyzer cannot respond to supply-pressure failure from a passage describing monitor placement and detection scope (R-2.4). The independent option evidence stage remains pending because the prerequisites failed. The saved draft remains held.

The follow-up changes make Studio recover the same completed item after a generation-receipt conflict and avoid asking the independent explanation model to grade two exact copies of an option explanation with identical allowed passages. Each stored field retains its verdict. Future MC plans distinguish directly measured inputs from downstream effects and avoid ambiguously asking which of several potentially concurrent equipment responses happens first. Future repairs also check that the case and lead-in are grammatical separate sentences. No accepted or held draft was rewritten again.

The isolated respiratory option-review attempt ([44394212998](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44394212998)) received provider HTTP 200 but recorded `REVIEW_RESPONSE_INVALID`. It made no authoring or rewrite call. The saved question hash remained `af1ed297de38c0f058053067fe4ebc3f760af2f8d238be9b635e24eb0d144c4c` and the draft remained 9/10 with a pending option judgment. The follow-up constrains the Qwen MC option response structure while allowing explicit uncertainty and retaining the existing source, coverage and verdict checks. No completed clinical judgment was regraded.

The [follow-up saved-review run](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44395224336) used application `f5a826025e4ede2edaa542e61820a5217456388f`, build `9bb497a7-b80a-4e5c-b9c3-fa7650a3b061` and container image SHA-256 `3e9a8a74f61c8a1ff9115ab69936f472a38224a32519530049d04fcc265e24b4`. The structured option response passed. Respiratory draft `f6440562-8a49-4293-8d67-d78e8773b811` now passes **10/10** automated checks, with zero current-source revalidation issues. Its question hash and one-rewrite count stayed the same. Human review remains pending. The stem wording issue noted above still needs review. No question was approved or published.

| Exercise | Saved draft | Automated checks | Result |
|---|---|---:|---|
| Lecture, shunt versus dead space | `f6440562-8a49-4293-8d67-d78e8773b811` | 10/10 | Current-source revalidation clear. Pending human clinical review and stem wording review. |
| Freeform, oxygen supply pressure failure, initial source-scope change | `b34d2cdb-7acf-4831-8a27-8005476e0535` | 7/10 | Held for blind-answer disagreement and unsupported C explanation. |
| Freeform, oxygen supply pressure failure, concurrent-response correction | `0c719d71-3510-4063-ae90-d2a647c42bf5` | 7/10 | Blind and changed-case checks passed. Held for cues and unsupported C explanation. |

The last equipment request ([generation run](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44395473045), [completed-only recovery](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44397164390)) used one rewrite and completed after the runner exhausted its first polling window. Recovery saved the same result. The reviewer identified the key in four of five stem-free trials (R-12.2). Option C's rationale and evidence map combined the gauge-display claim and the fail-safe cutoff claim, but the cited passage did not establish the cutoff mechanism (R-2.4). Independent option evidence correctly remained pending. Current-source revalidation returned three issues. The next equipment change should test a single response form, avoid including the uniquely protective action in an option that asks for a device, and separately cite any indispensable second claim. A further full generation on the same build would not test a new correction.

There are **three** unpublished drafts with all ten automated checks passing. The local-anesthetic and FRC drafts and the new respiratory draft all await human clinical review. This batch established one new automated pass. Reliable first-pass generation across new topics and actual personal lecture-file upload in the browser remain open.

### Lecture upload acceptance and larger batch scope

The primary workflow is an uploaded lecture file yielding original MC questions on its learning objectives. The lecture defines coverage. Trusted indexed textbook passages must support the key and affirmatively explain each distractor. A file extraction or plan is successful only for planning purposes. Count a question as an automated acceptance only after saving the draft, passing all ten checks and clearing current-source revalidation. Clinical review remains a separate requirement.

Application `d3e7dfa01bb7eae236a5dcbd7e986b0734d1af84` instructs the author to keep all choices in a single response form and keep distractor explanations within the facts their citations establish. It doubles the time window for read-only completed-item polling without adding authoring calls or changing the one-rewrite cap. A disposable lecture PDF with the oxygen pressure failure objective is the live control ([run 44425197139](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44425197139)).

Requested sizes of 25, 50 and 100 follow the lecture-to-question quality milestone. Treat each size as an upper target for one resumable batch. Record each question against its lecture objective, enforce the same independent gates, and show counts for drafts that pass, are held, or lack sufficient grounded concepts. Resume by item identity and preserve completed drafts through disconnections. A target count should never force duplication or lower evidence standards.

The live service extracted the sample PDF, selected its oxygen pressure failure objective (II.A.6), and generated one unpublished draft, `72bc2fa2-8b69-4ccd-8a01-984629599bfe`. The draft scored **8/10** after one rewrite. It passed the options-only cue check, the blind answer check and the editorial check. R-2.4 held the option C explanation in both fields because the citation established the alarm trigger but did not establish the broader claim about what the device does not measure. Independent option review remained pending. The uploaded bytes went through the same file endpoint used by Studio. This was an authenticated service verification with a sample PDF; browser interaction with a personal lecture file remains unverified.

The saved stem also ended its case mid-phrase before the standalone question. A deterministic regression check now holds that construction using the existing authored counterfactual boundary, even when the editorial model misses it. The one-rewrite guidance calls for a shorter, complete condition and an explanation grounded in the explicit trigger described by the citation. The failed draft remains held with its original result and one rewrite.


### November 19 highlighted personal lecture controls

The attached Peripheral Nerve Stimulation PDF was inspected locally. Its four yellow highlights are flattened drawings, with bold text on all 19 pages. PDF extraction now carries both forms of emphasis into MC topic priority. Short marks such as "Gold standard" use a nearby bold section subject when available. The correction avoids allocating a separate question to that generic phrase. The lecture regression suite passed 53 tests before this correction was committed.

The browser reached the authenticated staging AI workspace. A read-only plan from the extracted page 13-14 text initially allocated Mechanomyography and Gold standard. The file chooser then failed and the workspace connection was lost. Actual upload of this personal file through the browser remains unverified. The next service verification used the two extracted emphasized subject names and an explicitly selected II.C.4 objective. It did not upload the PDF or establish full-lecture coverage.

[Run 44534610580](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44534610580) verified application 24959edc87f2e02c0465d70f788e31b65e0d0844, staging build ed8c42ea-0e05-4255-9e2c-9af93a928f8f, and settled image b85c2c467d22c66bb1520e5d88e9902173bc48848156e3b54362b5a0f4b2f02f before the two requests. Each used one rewrite.

| Highlighted subject | Saved draft | Automated checks | Exact blocker |
|---|---|---:|---|
| Mechanomyography | 983b392e-1348-4e53-83a3-501ab348a1f1 | 8/10 | R-2.4 on B, C and D rationale/evidence explanations. Their cited passages did not establish the complete comparison with the case. Independent option review remained pending. |
| Acceleromyography | bc29d368-58c1-40a6-a72c-5e48804a6def | 8/10 | R-2.4 on D rationale/evidence explanation. Its passage did not define kinemyography as distinct from the acceleration technique. Independent option review remained pending. |

Both passed schema, math, evidence traceability, duplicate, blind-answer, cue, deterministic writing and editorial checks. Neither passed acceptance. Neither received a second rewrite or repeated grading.

The private MC plan previously allowed exactly one passage per option explanation. The next correction allows one to three source references per option, each with validated passage and span IDs, so a comparison can cite both the case-defining criterion and the alternative's definition. Existing single-passage plans remain readable. Independent explanation and option review still adjudicate the claims. The author must replace a distractor when no retrieved source establishes the necessary distinction. The new schema uses authoring contract 2026-11-19-v25. Regression and live verification of this change are pending below.


The multi-passage control used [run 44537179981](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44537179981), application 3f6d0ca1f39d4db1df7da6470c01db6bbc622d24, build 67984a46-0ddb-4800-9d7b-8c06622ae9a6 and settled image bc9845fc9134f8ad3413eb7f009e4392637447a86aaeec2b24ffeec55d8afbff. CI passed 1,087 Python tests (five skipped), 209 Node checks and repository validation.

Fresh mechanomyography draft bc68b848-8fdc-4d05-b3ad-9ef1a6730e73 used the new multi-passage format. Its final option citation counts were A=2, B=1, C=2 and D=2. It remained **8/10** after one rewrite, held for R-2.4 on C and D explanation fields. The EMG comparison did not cite the needed force-transducer definition, and the KMG comparison still relied on source silence. The format change worked, but additional citations alone did not fix the explanation. No new question passed acceptance.

A read-only index check found direct kinemyography definitions in existing passages, including af4bdfb9-63ec-4ce2-a06d-cc1b89dc9ff2 and fa3536f9-f5b1-4e1b-92b9-814408b3c371. The next correction retrieves up to four fresh passages specifically for source-held options before the same sole rewrite. It retains the authenticated owner, selected books and physical page/section scope. Supplemental source IDs and a source-packet hash are recorded separately from the initial preflight evidence hash. All cited passages remain subject to source revalidation before approval. This performs no new authoring call and gives no additional rewrite to an existing failed draft. The resulting authoring contract is 2026-11-19-v26.


The targeted-retrieval control used [run 44540228595](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44540228595), application bec67702c4a4703fe89b3a6d9d8bdb5857999133, build 7741a208-1714-4cb2-87bb-b560e7b9ca7e and image ba94d0562e66c4040786da09c6b5ebf4855cf920a29506956d4b8faa67cd5668. CI passed 1,090 Python tests (five skipped), 209 Node checks and repository validation.

Draft f1a5c7e8-fe9b-4b13-a8e8-dd25560cb0ee saved at **8/10** after one rewrite. The repair retrieved four scoped passages, including the two direct KMG definitions identified above. Its source packet hash was 48951190c0c89f1289751d68d7aba29397e7b410a003a8ef7d7d520eb82428af. Source review now held only the D explanation fields. The rewritten explanation positively described the KMG strip and compared it with the case's force-transducer ring, but cited only the KMG passage. That passage did not establish the case apparatus. The source reviewer correctly required support for the complete comparison.

The next correction supplies each MC option comparison with the key's already-cited case evidence as well as its own definition citations. It introduces no new source, explanation or clinical verdict and does not include unrelated global evidence. Initial plans and the sole rewrite both use this transport step. All source support remains independently adjudicated. The existing held draft stays unchanged. The resulting authoring contract is 2026-11-19-v27.


### November 19 case-evidence result and missing-review diagnosis

The case-evidence control [44543324802](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44543324802) verified application `54d8d69bb00fa1f515fa42dac6340a99c86dac2d`, build `0a99007a-9e60-4d7a-afd5-eef39e715470` and image `acea403bd3ccf9dcdd301eb764d131088cf3b38bc6d3fa7c014c40a18a1da1b0`. Mechanomyography draft `0db56e8d-41ec-4f99-9276-e88c31aaee1c` saved at **9/10**, with one rewrite and all explanation evidence passing. Independent option adjudication returned an invalid response. Current-source revalidation held only that pending review; it did not establish acceptance.

An isolated missing-review control [44637998783](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44637998783) made one review request on the same saved question. The result again recorded `REVIEW_RESPONSE_INVALID`, with no completed judgment. The question hash stayed `c1ce3838eb4354b7edb952babcb2106728c66f503e5572b0be22fbf9e1c838a1`, the rewrite count stayed one, and no generation, rewriting, approval or publication occurred. Do not repeat this review on the same build. Three prior automated passing drafts remain pending human review.

Inspection identified an independent response-handling defect: the strict MC response schema permits an uncertain judgment with empty references, but hydration rejected it as an invalid provider response. Hydration now preserves that explicit uncertainty and its empty quotes. The existing evaluator holds the question, retains the completed negative judgment, and makes it ineligible for missing-review resampling. Supports/refutations still require authorized verbatim evidence. Regression covers adapter → hydration → handoff → screening → replay eligibility. This is a demonstrated offline defect, not a claim that it explains the earlier live responses.

The handoff now records only allowlisted validation-detail codes for malformed JSON, missing/duplicate option judgments, source aliases and invalid/unauthorized quote references. Arbitrary exception text is excluded. The next bounded review can diagnose any remaining invalid response without logging model output or source text. Authoring contract: `2026-11-19-v28`. Fresh live verification remains pending.

Offline validation: 1,094 Python tests ran (four skipped); 104 gateway/relay Node checks passed; repository validation and diff checks passed.


### Scoped independent option response

The diagnostic-only follow-up [44638590506](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44638590506) verified application `7d28177a3326815a127014a1aa8c3512d134c21f` after successful CI and build `8167821b-3f20-4e6d-bb37-5f45134cc1b7`. Its sole review again left the unchanged saved question at **9/10**, now with the fixed detail `option_quote_ref_scope_invalid`. No clinical judgment was returned; the source-reference hydration failed. This localizes the failure to an unauthorized, uncited, or passage-mismatched quote reference; the generic detail does not distinguish those subcases. No new question passed acceptance.

The previous strict response schema used global passage and span enums and allowed repeated option IDs. The correction defines a response object keyed by every option ID, with each option's quote references restricted to its own retrieved passages. Each passage has its own span-ID enum. The trusted adapter restores option IDs from those map keys and passage IDs from the selected quote references; it never invents or changes clinical verdicts, explanations or source text. Legacy array responses retain all existing validation. Missing/extra options, injected identities, cross-option citations and wrong spans remain blocked. Explicit uncertainty remains a retained blocking judgment.

This uses the documented JSON Schema `anyOf` subset in [Groq structured outputs](https://console.groq.com/docs/structured-outputs). The evaluator, blind-answer boundary, contradiction review, verbatim-quote checks, one-rewrite limit and human review remain mandatory. Authoring contract: `2026-11-19-v29`. Local checks: 1,095 Python tests ran (four skipped), 104 gateway/relay Node checks passed, repository validation and diff checks passed. Deployed acceptance of the scoped format is pending.
