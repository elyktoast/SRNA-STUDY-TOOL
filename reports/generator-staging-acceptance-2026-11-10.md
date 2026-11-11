# One-question staging verification — November 11, 2026

## Verified outcome

One fresh authenticated staging generation passed the source, schema, wording,
blind-answer, teaching, editorial and independent option-evidence checks and
saved exactly one private unpublished draft. No rewrite was needed. No approval,
publication or production/main merge was performed.

- Draft: `43d13b5b-bceb-483a-bec0-d3c77231a45b`
- Item: `b7d4b4cf-23db-48f5-915a-7ae53c917076`
- Saved: 2026-11-11 01:01:56 UTC
- Status: `pending_review`; `reviewed_by` and `reviewed_at` remain null.
- Classification: NCE MC, I.A.2 Respiratory, application.
- Source: owned, ready indexed `Nagelhout__Elisha_.pdf`, PDF pages 731–732.
- Both stored excerpts and their PDF pages match the current owned index exactly.
- All 24 explanation-support quotations and all nine independent option-review
  quotations were separately checked as verbatim current indexed text.
- The independent key judgment cites both source passages and both tested
  measurements. Every wrong option has an affirmative source-grounded refutation.
- The final clinical case, four choices and four-part teaching rationale were
  inspected after persistence. Full question text and copyrighted excerpts remain
  in the private staging bank rather than this public report.

| Check | Result |
| --- | --- |
| Canonical v2 schema and deterministic wording | Pass |
| Indexed source, page and excerpt validation | Pass |
| Fresh independent blind answer | Pass |
| Concept and rationale source review, all 15 fields | Pass |
| Independent editorial review, all seven criteria | Pass |
| Changed-case fresh blind answer, different correct choice | Pass |
| Five shuffled options-only trials | Pass; zero keyed guesses |
| Independent retrieval and adjudication of all four options | Pass |
| Save once and subsequent authenticated draft retrieval | Pass |
| Browser preview of the saved question and structured explanations | Pass |
| Human clinical approval | Pending; publication blocked |
| Semantic duplicate verification | Pending; publication blocked |

## Recovery fixes

PROVIDER_UPSTREAM covered distinct failures. Groq GPT-OSS authoring exhausted its
daily quota. Cloudflare GPT-OSS exposed response-contract failures and incorrect
shared-dependency reasoning in exact-source probes. Staging authoring now uses
Cloudflare `@cf/zai-org/glm-5.3`, its wrapped JSON schema, bounded low reasoning and
explicit step limits. Independent blind, editorial, explanation and option
reviews use Groq `qwen/qwen3.8-27b`, separately from the author. Blind requests
exclude the author key. Gemini and legacy hybrid generation remain disabled.

Incomplete option-review responses also produced PROVIDER_UPSTREAM. Temporary
source aliases shorten output while preserving real passage IDs and per-option
retrieval authorization. Unknown or unauthorized references, nonverbatim quotes
and missing paired-key coverage fail. Retrieval retains two context passages and
a direct option match within a three-passage budget; it never supplies a verdict.

v19 failed DRAFT_PLAN_CONDITION. The generator now inserts the authored clinical
case at one explicit stem slot before strict binding, rationale generation,
validation and independent reviews. Missing, duplicate or conflicting cases are
rejected; clinical prose is never inferred or silently repaired.

The v20 API test passed, but post-save inspection found unsupported exclusive
physiology in its teaching explanations. That acceptance is superseded and its
draft `49f52ff1-1826-4197-87f6-9f5bb18a5cea` is marked `needs_revision`. The existing
exclusivity guard covered drug/class lists but missed causal wording such as
“increased only by.” v21 extends it to causal physiological assertions and the
key explanation. Replaying the old source-review report flags all five affected
fields without provider calls. Nonexclusive statements and explicitly supported
exclusive claims remain supported. The earlier v16 paired-evidence acceptance is
also superseded; earlier failed candidates remain unpublished and flagged.

Disconnect recovery polls only an owner/request/source-bound completed checkpoint.
Incomplete recovery fails before any model adapter is constructed. Recovery
cannot restart paid authoring, preserves the original request/item ID and uses
save-once persistence. Synthetic disconnect integration and server no-fallthrough
regressions pass; the final live run completed without a disconnect.

One protected rewrite remains the maximum. Authentication, source authorization,
independent review and publication gates remain in force. Textbook extraction,
indexing and all five canonical formats are preserved. No database schema,
indexing or existing learner/question-bank changes were made.

## Verification and deployment

Backend runtime source: `7aaca84b8a60e851ead7cac5f06cbe31fc1f42d2`.
Authoring contract: `2026-11-11-v21`; quality contract: `2026-11-10-v2`.
Preview/readiness source: `fd7b78e191aa44840a6716a4ce2263f76aa8d6e4`.

- [Backend CI 42934580281](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42934580281):
  894 Python tests ran with one skipped; all 132 Node tests passed, as did the
  container build and repository validation.
- [Final UI CI 42936363654](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42936363654):
  894 Python tests ran with one skipped; all 134 Node tests, container build and
  repository validation passed. Local performance budgets and four additional
  targeted rollout-predicate tests also passed.
- [Staging deployment 42934708221](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42934708221):
  image upload succeeded but the four-minute readiness deadline expired. The
  replacement subsequently finished at 00:58:46 UTC without health errors. The
  deadline now allows ten minutes; active-rollout, image, health and quiet-period
  safety requirements remain unchanged. This root-level readiness change and the
  browser rendering fix do not change the tested backend image.
- [Live acceptance 42934711111](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42934711111):
  the separate readiness retry passed without rebuilding. Authenticated manifest,
  page-image preview, CORS/auth boundaries, indexed preflight, exact v21 runtime
  and configured provider metadata passed before paid generation. Generation,
  independent checks, save and authenticated read passed at 01:01:57 UTC.

Local Python has a different PDF runtime and reproduces the previously known
image-placement fixture mismatch; CI runs the complete suite successfully.
Extraction code was not changed to accommodate the local dependency difference.

## Browser and release state

The saved-question preview now renders the structured core concept, key reasoning,
trap and each wrong-answer explanation, plus objective and PDF-page citations.
In the owner’s signed-in browser, the saved draft opens with all four teaching
sections, the wrong-choice explanations, I.A.2 and both PDF page citations.
Legacy string explanations remain readable. Model content is inserted as text,
never HTML; both behavior and safe rendering have regressions.

The isolated Pages project `srna-study-tool-staging` tracks
`fix/board-question-quality` so the canonical staging hostname serves the PR UI.
Its deployment label “production” refers only to this staging project, whose
domains are `staging.srnastudytool.com` and its staging pages.dev domain.
Frontend deployment `e627224c-731d-4e10-8d57-1ce9f7a0e598` matches the preview source
above and succeeded. Main remains `fa20a18e840cf6fa9466122fe511b5d5ba08a0ce`.
Return this staging project to main when the approved PR is released; do not
restore the older UI before that release. Changes are consolidated in PR #189.

## Limits

This verifies one staging flow, not batch reliability or empirical item hardness.
Response statistics remain fresh at zero/null; no quality score or psychometric
calibration was fabricated. Human clinical review and semantic duplicate
verification remain pending and publication remains blocked. The staging semantic
index is not provisioned; Gemini remains off. Edition and printed-page checks are
explicitly unrecorded/unverified; citations identify PDF pages only. Larger
batches and cross-textbook sourcing remain deferred as requested.
