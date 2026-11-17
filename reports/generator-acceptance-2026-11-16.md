# Generator acceptance — November 16, 2026

## Integrated into staging

- PR #190: teaching-first retrieval, reviewer defaults, accurate failed-draft state, opt-in block extraction and read-only source audit.
- PR #191: bounded multi-textbook scope through generation, option retrieval, persistence, revalidation and revisions; complete stored 1,600-character passages.
- PR #192: requested lecture counts, fair allocation across chunks, disposable PDF/PPTX live acceptance workflow.
- PR #193: ordinary single-component MC choices as well as optional crossed pairs per Standard v2.0 R-6.7; balanced all-library lecture planning; pasted-text `all` selection; explicit comparison baselines and no unsupported favorable-outcome inference.

Production and indexed passages have not been replaced. No question was approved or published.

## Verified evidence

[Read-only original-file sample](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43891117649) checked 30 physical pages across seven original source-bound PDFs. Block extraction conserved their original glyph inventories. Nagelhout still contains unmapped control glyphs; the OR guide lacks a matching source-version record and was explicitly blocked. This sample does not establish all-page reading order, table accuracy, clinical truth or readiness to replace indexes.

The exact multi-book draft INSERT ownership predicate passed seven read-only PostgreSQL cases: same book and another ready owned book allowed; foreign owner, unready source, spoofed passage/book pair, nonexistent passage and missing book field rejected.

## Live workflow results

[Run 43893723136](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43893723136) passed:

- Multi-book evidence preflight.
- Real disposable PDF and PPTX extraction/planning in MC, MS, SA, DD and HS, each producing the requested three preflight jobs.
- Multi-book scope in planned lecture jobs.
- Unsupported lecture-topic hold, without paid generation.
- Provider/checkpoint readiness and recovery of the original completed request without duplicate generation.

Its single paid MC sample was saved as `needs_revision`: schema, deterministic text, indexed evidence, explanation support, original blind solve and options-only checks passed. The changed-case independent solve disagreed after one rewrite (R-5.3). Independent option adjudication remained pending. This is not an accepted quality sample. The sample exposed an unstated directional comparison baseline and an unjustified favorable-outcome inference; PR #193 addresses those authoring/review instructions.

[Run 43895899023](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43895899023) repeated all ten lecture-format planning checks successfully and blocked the unsupported topic. Its paid call stopped at concept-plan response-field validation before creating a draft. No clinical gate was bypassed; finer state-count/state-length/option-length diagnostics and native output bounds are being added.

## Rollout race found in the next sample

[Run 43897366480](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43897366480) again passed all ten lecture planning checks. Its generation request failed with a non-JSON HTTP 500 during a container rollout. Cloudflare's exact-commit build did not finish until 15:34:26 UTC, after generation had already started at 15:34:15 UTC; the application configuration updated at 15:34:55 UTC. Logs explicitly reported termination for a new-version rollout. The old gate had accepted the previous deployment's stable state while the new build was still running.

The corrected gate requires the exact dispatched commit's Cloudflare Workers build check to succeed before its quiet period can begin. It also retains current image, instance state and health checks. Transient HTTP 500/502/503/504 responses now trigger only completed-checkpoint recovery; authentication, validation and rate-limit errors do not cause paid retries. Acceptance does not claim that this interrupted attempt passed clinical quality.

## Latest completed acceptance and remaining quality defects

[Run 43946900446](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43946900446) passed the exact-build gate, multi-book preflight, all ten PDF/PPTX format planning cases, unsupported-topic hold and provider/checkpoint readiness. It generated one MC item, used one automatic rewrite, reran review, and saved draft `14520cc3-f42d-4fb9-b340-00de12b04e6e` as `needs_revision`, unpublished.

Schema, deterministic text, indexed evidence and original blind solving passed. Explanation support flagged R-2.4; the changed-case test flagged R-5.3; five shuffled options-only trials flagged R-12.2. Duplicate screening and independent option adjudication remained pending. This is another failed quality sample, not evidence that generation is reliable. No gate was waived and no item was approved.

The original alternatives mixed mechanisms involving different named drugs and patient populations, making the key easy to identify from context. Its alternate case also retained a lead-in about the original-only symptom. Planning and bounded repair instructions now explicitly require competing answers under the same case context and a lead-in meaningful in both cases. The acceptance request now uses the studio's default full owned-library scope for the paid generation itself, not only its preflight probe. These changes require a new live acceptance sample before claiming improvement.

During this run Cloudflare reported an active rollout with idle instances, and authenticated catalog traffic received `instance_allocation_unavailable`. The rollout subsequently cleared and generation ran. The gate now permits bounded authenticated catalog-only warm-up attempts after exact-build quiet time while retaining all rollout/image/health requirements. Warm-up is not a capacity guarantee. A subprocess test proves this path exits before planning or paid generation even if a conflicting paid flag is present.

## Approval-boundary correction

Inspection of the review path found that citation/schema revalidation did not incorporate saved independent-review failures. The corrected revalidator carries forward all required automated stages and rejects missing, pending, flagged, failed or contradictory reports. Human-review pending is expected until the clinician makes the final decision. Numeric items additionally require trusted page-image verification; hotspot items require trusted figure verification. These integrations are still open and are not fabricated by this correction.

The storage review function independently locks the owned draft and rechecks its saved screening before any approval UPDATE, preventing direct callers from omitting the HTTP validation. Revision-needed rows and bulk selections cannot invoke approval from the UI. Tests cover current citation structure passing while saved explanation review fails, missing checks, pending duplicate/independent option reviews, direct storage rejection before mutation and HTTP 422 before review persistence. No real draft was approved to test this boundary.

## Cloudflare canonical duplicate-index integration

The current canonical export contains 9,000 IDs, 8,527 distinct stem hashes and 1,001,691 total stem characters; the longest stem is 3,199 characters. The existing private index migration is now applied to staging, with RLS enabled and no anonymous/authenticated table grants. It is not yet populated by this code change.

The new integration uses only `@cf/baai/bge-m3` through an authenticated, model-pinned native Workers AI binding. Gemini is absent from the active runtime embedding factory. Batches are bounded to 32 stems, 10,000 characters per stem and 128,000 total characters. Only finite nonzero 1,024-dimensional vectors are accepted. The resumable writer checks ownership, hashes, model and dimensions before paid calls, commits validated batches independently, and verifies complete canonical coverage before claiming readiness. It emits counts only and uploads no stem/vector artifacts.

The container builds its own IDs/hash inventory from the exact course manifests; it does not contain canonical stem text in that inventory. Completed generation checkpoints and semantic screening reports bind to its inventory digest. Approval rejects exact-only checks or semantic results from a different canonical bank version. Paid acceptance now requires complete matching runtime/index inventories before authoring and a passed duplicate stage afterward.

Unit verification: 1,027 Python tests (four skipped), 188 Node checks and repository/diff checks passed. Failure injection covers interruption/resume, ownership conflicts, stale hashes/models/dimensions, malformed vectors, unsigned or oversized relay requests, private export error logging and stale approval reports. The live indexing workflow also verifies an exact canonical-stem positive control and an unrelated-text negative control through the same full-bank lookup and cosine scorer. Live population, native binding response shape, complete reconciliation and a real generated candidate still require deployed verification.

## First live canonical index run

[Run 43956832836](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43956832836) confirmed the deployed native binding, signed relay, vector protocol and private database writes across four batches, durably saving 128 of 9,000 entries. The fifth relay invocation returned HTTP 503; Cloudflare request telemetry confirmed four HTTP 200 responses followed by that HTTP 503. No question generation ran. Complete coverage and live controls are not yet proven.

The embedding adapter now makes at most four identical attempts for explicitly transient transport failures, with bounded backoff; authentication/configuration failures and invalid vectors are not retried. This applies only to embeddings. Paid question authoring remains single-attempt. The CLI reports fixed provider-rule/SQLSTATE categories rather than private exception text. Resume must skip the 128 already validated rows and still require complete reconciliation and both live controls. A marker-gated push on the dedicated staging indexing branch can run the same protected index-only workflow when browser dispatch is unavailable; the manual workflow remains supported.

The deployed approval UI and backend were also checked against draft `14520cc3-f42d-4fb9-b340-00de12b04e6e`: its approval button is disabled, and read-only revalidation retained blocking checks for duplicates, explanation support, editorial quality, options-only screening and independent option evidence, with no model calls or database writes.

## Open acceptance requirements

[Run 43945411972](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43945411972) confirmed the exact-build deployment gate and multi-book preflight (seven books, eight passages), then encountered a TLS connection reset during the first read-only lecture plan. It made no paid generation call and created no draft. The acceptance client now allows at most three attempts for explicitly enumerated read-only planning/readiness operations on transport failures or HTTP 502/503/504. Generation, writes, unknown endpoints, validation/authentication errors, HTTP 429 and HTTP 500 are not retried by this helper.

1. Representative generated drafts that pass all applicable automated reviews; one success does not establish consistency.
2. Independent per-option/component evidence and source checks on a small varied batch, including semantic duplicate screening.
3. Numeric original-page verification and independent recomputation for SA; a real licensed/original figure and verified region placement for HS.
4. Full format-specific preview, scoring and accessibility acceptance before alternative formats reach learners.
5. Broader source-layout validation, Nagelhout symbol interpretation and OR-guide provenance recovery before index replacement.
6. Human clinical approval remains required by Standard v2.0; automated checks never publish.


## Canonical index batch and database adaptation fixes

PR #201 split embedding requests by padded UTF-8 context rather than total characters alone. Canonical text is preserved; the signed relay enforces the same input bound and reports permanent context rejection without private provider details. CI passed 1,030 Python tests (five skipped on that runner), Worker tests, the container build and repository validation. Staging build `6a7bc399-b7d2-4dc3-b1e9-cab39b7e0311` deployed merge `f294e415fdc25b65a844bfb92474716bc740da6d` successfully. The separate feature-branch preview failed because this container project has no isolated preview configuration; it did not deploy.

Index-only run [43991889373](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43991889373) resumed from 128 and saved 1,501 entries before an unclassified interruption. A metadata-only exception-class diagnostic in [43992404491](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43992404491) identified `DataError` after progress reached 3,709. Native request telemetry returned HTTP 200. An offline reproduction with psycopg 3.3.9 confirmed that a list containing both integer zero and a float raises this exact exception during array adaptation, whereas a homogeneous float list succeeds.

The writer now converts already validated numeric components to Python floats before database adaptation, preserving all numeric values and leaving provider responses unchanged. A regression verifies mixed native integer/float vectors are stored as homogeneous floats. Errors expose only an exception class, fixed provider rule and SQLSTATE; no private messages, questions or vectors are logged. Complete 9,000-entry reconciliation and positive/negative live controls still need a successful resumed run. No questions were generated, approved or published during these index jobs.


## Complete population and collation reconciliation

[Index run 43993044367](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43993044367) reused the 3,709 saved entries and completed all 9,000 canonical embeddings after homogeneous-float adaptation. All rows have 1,024 dimensions and no null components. Its final validation failed closed before declaring readiness.

The staging database uses `en_US.UTF-8`, while the Python completeness checks compare Unicode identifier order. A read-only full-bank query measured one ordering inversion with the database default and zero with explicit `COLLATE "C"`. Both reconciliation and exhaustive candidate lookup now use C collation for the keyset boundary and ordering. Mixed-case, multi-page regressions exercise complete traversal. This correction reuses every saved embedding; it requires no re-embedding of the bank. Known-duplicate and unrelated-text controls remain required before claiming duplicate screening is ready.


## Live canonical duplicate screening verified

[Run 43993956728](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43993956728) passed complete reconciliation and both real controls against all 9,000 saved entries. It reused every entry (`new_embeddings: 0`, `remaining: 0`, `complete: true`). The exact canonical-stem control was detected; the unrelated-text control returned zero matches at the provisional 0.85 threshold. Both controls used the same exhaustive lookup and cosine scorer as generated candidates. No questions were generated and no drafts were written by that run.

Canonical inventory digest: `44e9be2173cac71a71f51e3cfe48b3712d3ad301e8d076f01796a3aee50497a5`. PR #203 merged as `c0f9c6433d62487325aab6748acf6875690cb508` after its staging checks passed. A fresh one-question, all-indexed-textbooks MC acceptance was submitted as [run 43994253848](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43994253848). Its result is still pending; index controls alone do not prove generator quality or calibrate semantic similarity against expert-labeled near-duplicates.


## Authenticated readiness route integration

[Acceptance run 43994253848](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43994253848) passed its settled-deployment gate, seven-book/eight-passage preflight and all ten PDF/PPTX format plans, then stopped before any paid question generation because the gateway had not exposed `/generation/index-readiness`. The backend and acceptance client already supported this read-only route.

The gateway now authenticates and forwards GET-only readiness, rejects query parameters, and validates an exact metadata-only JSON response with a canonical inventory digest, bounded counts and internally consistent readiness. Missing credentials, production origins, POST, contradictory counts and extra response fields fail closed. No individual question identifiers, stems or vectors are exposed by this endpoint. A fresh acceptance run is required after deployment; the previous run produced no draft.


## First live question with complete semantic screening

[Run 43995269518](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43995269518) verified the deployed read-only index-readiness endpoint (`ready: true`, 9,000 expected/indexed), all ten lecture-format plans, source evidence and active non-Gemini providers. Its new item ID was `b4b045d7-b25f-462d-8938-0e6c7737bb6d`. Authoring, rationale and independent reviews ran, followed by one rewrite. It then returned a generic validation error and saved no admin draft; the checkpoint remains partial and must not be automatically resumed for another rewrite.

A regression reproduced the exact repair-path exception: the recursive screening call supplied the original candidate's vectors together with the live semantic-lookup callback, which the exclusive-input guard correctly rejects. A second regression showed that pre-supplied vectors could otherwise be reused after a rewrite. The handoff now discards candidate-dependent vectors before rescreening: a live callback embeds and searches the revised stem afresh; without one, duplicate verification remains pending. Both cases preserve the one-rewrite limit, rerun screening and never auto-publish. Twenty focused screening tests pass, including the two failures reproduced before the fix. A fresh question request is required for deployed acceptance.


## Full pipeline and completed-only recovery exercised

[Run 43997761332](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43997761332) generated an MC question on local anesthetic ionization and onset, performed one rewrite, reran screening and saved exactly one unpublished draft: `0fc379a9-38dc-49ac-90be-e9b50cf0828c`. Schema, math, evidence, full-bank duplicates, blind solving, source-supported explanations, editorial quality, options-only trials and independent option evidence all passed. Deterministic text remained flagged for R-2.8 (eight consecutive textbook words in the stem), so the draft correctly remains `needs_revision` and the acceptance run failed its final status assertion. Human review remains pending; no question was approved or published.

The initial request disconnected during long reviews. Completed-only recovery waited for the saved response and returned the same draft without repeating paid authoring. Its polls unnecessarily reconstructed a full semantic index before reading the completed checkpoint. Recovery now skips that factory while retaining authenticated owner/evidence/request fingerprint checks and the backend's no-generation recovery guard.

The R-2.8 diagnostic now identifies the exact field and zero-based word range without echoing source text. Source eight-word windows are precomputed once, preserving the original strict threshold. Planning and rewrite instructions require original wording; stem paraphrases must also update the exact counterfactual phrase so answer verification still applies. The existing draft will not receive a second automatic rewrite or inherited approval; a fresh sample must verify these changes.

## Real AI Studio generation and draft-list concurrency

After PR #206 deployed successfully, one authenticated AI Studio request saved unpublished draft `1925376c-b22d-41ab-b113-07af67c9b5c2`. Its completed checkpoint confirms one request and one automatic rewrite. Nine automated stages passed: schema, deterministic text, math, evidence, full-bank duplicates, blind solving, editorial quality, explanation evidence and independent option evidence. This verifies the original-wording repair on a fresh sample. Options-only review remains pending after three completed trials; human review is also pending. `pending_review` is a storage status, not proof that all automated checks passed. Backend approval requires the missing stage to pass, and no approval or publication was attempted.

Read-only relay telemetry shows HTTP 200 for the four final options-only calls. This does not prove their response validity; the old reviewer swallowed exceptions without a reason. The reviewer now records only an allowlisted provider rule or a fixed invalid-response code and completed-trial count. It neither retries failed trials nor converts incomplete reviews to passes. Raw provider messages and source or option text remain excluded. The precise cause of this sample's incomplete trial is unresolved; another authoring call is not justified solely to recover diagnostics.

The live draft workspace also exposed a race: two overlapping list requests each appended the entire collection. Rendering now accepts only the latest request, clears the list after its response arrives, and removes stale bulk-selection state. A stale request failure cannot replace a newer successful view. The actual pre-fix render function produced two headings in an offline concurrency reproduction; the fixed function produces one. Two regressions cover reversed response completion and stale errors. This changes list rendering only; review decisions and approval requirements remain intact.


The same UI inspection showed that `pending_review` alone enabled approval even when an automated stage was pending. The authenticated list now returns only an `automated_checks_passed` boolean computed by the existing backend approval gate, without exposing screening contents. Single and bulk approval stay disabled unless this flag is explicitly true and the draft has no failed status. Server-side revalidation and clinical notes remain required. Tests cover legacy/missing flags, pending trials, fully passing reviews and failed-status precedence. Validation: 194 Node checks and 1,041 Python tests passed (four Python tests skipped locally). CI initially caught a missing frontend build-ID update; the corrected manifest is included.

## Current scope: usable MC generator first

The owner has explicitly paused development of MS, SA, DD and HS. Their previously documented verification gaps remain open but do not block finishing the MC milestone. No alternative-format feature work is included in this round.

MC acceptance requires: lecture-derived or freely selected topic/objective; ready trusted textbook evidence; a single best answer with relevant, plausible distractors and separately supported explanations; every applicable automated review completed; exactly one bounded automatic rewrite; durable unpublished save/recovery; readable review results; and clinical review before bank approval. The existing 9,000-entry duplicate index is complete and must be reused, not rebuilt. A small varied MC acceptance set is required before calling this usable; one lucky pass is insufficient. Production promotion and bulk publication are not authorized by this scope change.

Run [44006229971](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44006229971) is a fresh single MC request against the deployed PR #207 version, with safe incomplete-review diagnostics enabled. It completed successfully: draft `8da6a89a-26b3-44dd-ad42-a70405dc6e23` passed all ten automated stages, used zero rewrites, returned no generator issues and was durably saved unpublished. Human clinical review remains pending. This is one complete MC success, not yet varied-topic acceptance.

The next reliability batch constrains the options-only review response to exactly the expected JSON shape and current shuffled option IDs. Its schema admits every option and receives no stem or answer key; it cannot manufacture a correct review result. Invalid input is rejected before a provider call, and incomplete or flagged reviews remain blocked. This changes output structure, not the five-trial statistical threshold or one-rewrite limit.

The MC preview and saved editor now show a readable ten-stage checklist, including completed cue-test trials and explicit blocked status. Edited revisions cannot inherit the original question's checklist passes. Dashboard data arriving after navigation no longer replaces the selected AI view. The one-question acceptance client checks lecture plans only for the requested format and reuses its identical preflight response, reducing redundant calls while the other formats are paused. Local validation: 198 Node checks passed; repository validation and diff checks passed. Live structured-response and UI acceptance remain pending deployment.
