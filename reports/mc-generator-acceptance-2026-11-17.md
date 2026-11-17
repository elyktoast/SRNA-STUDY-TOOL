# MC generator acceptance — 17 November 2026

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
