# Board-question quality enforcement

## Scope and baseline

Baseline main: fa20a18e840cf6fa9466122fe511b5d5ba08a0ce. The previous saved
question passed configured source and blind-answer checks but did not satisfy
the complete NCE/SEE Item Generation Standard v2.0. Full document review found
obsolete authored content, an airway objective applied to malignant hyperthermia,
a restated counterfactual, faulty trap logic and an empty self-check.
The prior recovery report is a historical operational milestone, not a full
standard-compliance certification.

## Changes prepared

- Use the existing NBCRNA taxonomy for objective labels and supported numbered
  paths. The official 2024 outline confirms III.H.4 is difficult airway management
  and IV.B.4 is obesity. The Question Studio now requires an explicit objective
  choice rather than silently defaulting every subject to III.H.4.
- Reject authored halothane, ranitidine and bleeding-time examples unless the
  stem explicitly identifies a historical item. Preserve indexed source text.
- Add distinct-model independent editorial screening of blueprint fit, covered
  options, relevant context, a stem-variable counterfactual, trap logic, actual
  reasoning level and plausible single-flaw distractors.
- Add five fresh options-only trials with independent permutations and IDs.
  Stem, key, rationale and error-pattern tags are withheld. Flag an exact key
  guess rate whose one-sided binomial probability is at most .05 under chance
  1/C(number of choices, number selected). Missing/invalid trials remain pending.
  Passing is a screening result, not proof that no answer cue exists.
- Definite quality failures join the existing one protected rewrite and complete
  independent recheck. Pending/outage results do not consume a rewrite.
- Record server-observed rule results, failed-then-fixed rules, blind result and
  pending checks in self_check. Never preserve model-claimed approval. Initialize
  fresh-item response statistics and make the keyed option error pattern null.
- Attach available chapter metadata and explicit unverified printed-page state.
  Edition metadata is not recorded in the present textbook table; retain null
  and an explicit not_recorded status rather than inventing it.
- Keep Gemini excluded, indexing untouched, existing revisions protected and
  human approval/publication blocked. Larger batches and cross-textbook work
  remain deferred. Semantic duplicate coverage remains pending.

## Validation so far

Nine new focused Python tests passed. Local full suite ran 858 tests with one
skip and the previously known local PyMuPDF image-coverage fixture failure; no
new test failure remained after preserving legacy revision option metadata.
The two targeted Node suites passed 58 tests. Repository validation and
performance/architecture budgets passed. CI and live staging acceptance remain
required before this change is called verified.

## Live acceptance plan

First, a read-only paid regression must reject the previously missed blueprint,
counterfactual and trap defects in the saved prior item; obsolete content must
also be rejected deterministically. Then generate exactly one fresh indexed
question and require all current source, blind, independent option, editorial
and options-only checks. The final item must remain unpublished, and its stem,
choices and explanations must be inspected before judging quality. No question
text, source excerpts, prompts or provider reasoning belong in public reports.

Production deployment requires owner approval under the governing standard
R-17.4.5. Main merges trigger GitHub Pages deployment, so keep this consolidated
PR open until the staging results are reviewable and approval is available.


## First live boundary check

Source CI ran 858 Python tests without failures (one skipped), but repository
validation caught the missing frontend build-ID bump; that identifier is now
updated. The staging reviewer deployed and its first paid editorial control
stopped on provider HTTP 400, before grading. The new editorial prompt lacked
an explicit JSON-output instruction; the request is corrected and covered by
a provider-contract test. Sanitized pending-review diagnostics are added.
Choice-specific editorial/cue checks are scoped to MC/MS, preserving existing
numeric, matching and hotspot validation. A fresh live control remains required.


## Preserve source reviewers; verify a reasoning-capable editorial reviewer

CI run 42700698499 passed all 860 Python tests (one skipped), 113 Node tests
and repository validation. The corrected JSON request ran live in deployment
42700696568, but Qwen caught only the ineffective counterfactual and a context
issue; it missed blueprint fit and the faulty trap. That negative control failed
and no fresh generation was started. A separate read-only attempt to enable
Qwen low reasoning with hidden output was rejected by the provider
(42701621310); no unsupported request setting is retained.

Editorial-only screening now uses the already supported Groq GPT-OSS 20B model,
distinct from GPT-OSS 120B generation. Qwen remains unchanged for blind answers,
source evidence and options-only trials. Signed relay checks bind each step to
its authorized model; an editorial model cannot answer a blind/source-review
request. Live verification is still required.

The options-only binomial calculation is a conservative screening reference
under an independent chance-guess assumption. Repeated model responses may be
correlated; it is not a validated psychometric p-value or a numeric item-quality
score. Flags require review; a pass does not establish that the item has no cue.
