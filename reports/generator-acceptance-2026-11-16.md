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

## Open acceptance requirements

[Run 43945411972](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/43945411972) confirmed the exact-build deployment gate and multi-book preflight (seven books, eight passages), then encountered a TLS connection reset during the first read-only lecture plan. It made no paid generation call and created no draft. The acceptance client now allows at most three attempts for explicitly enumerated read-only planning/readiness operations on transport failures or HTTP 502/503/504. Generation, writes, unknown endpoints, validation/authentication errors, HTTP 429 and HTTP 500 are not retried by this helper.

1. Representative generated drafts that pass all applicable automated reviews; one success does not establish consistency.
2. Independent per-option/component evidence and source checks on a small varied batch, including semantic duplicate screening.
3. Numeric original-page verification and independent recomputation for SA; a real licensed/original figure and verified region placement for HS.
4. Full format-specific preview, scoring and accessibility acceptance before alternative formats reach learners.
5. Broader source-layout validation, Nagelhout symbol interpretation and OR-guide provenance recovery before index replacement.
6. Human clinical approval remains required by Standard v2.0; automated checks never publish.
