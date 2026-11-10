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


## Combine explicit writing guards with independent semantic judgment

The editorial-only 20B live control in 42702177333 caught the wrong blueprint
label, but missed the restatement and nonspecific trap. The gate remained failed;
no new question was generated. Add necessary deterministic writing conditions:
the counterfactual must explicitly express a changed condition, and the trap
must identify a specific incorrect choice by ID or full choice text. These
conditions are not proof of a valid counterfactual or causal learner-error logic;
the independent semantic checks remain mandatory. Diagnostic reports distinguish
model findings from deterministic findings. Tests ensure a model's blanket pass
cannot override missing specificity and that a well-formed but incoherent trap
still fails independent screening. Per-rule self-checks retain individual
editorial criterion results instead of treating every criterion as failed when
only one was flagged.


## Fresh v1 generation rejected; require a demonstrated counterfactual

After deployment 42703637120 and all four browser shards in 42703637236
passed (production deployment skipped), fresh acceptance 42754450165 created
draft b9880dde-631b-41a2-b684-c57871f89770. It remains unpublished. The candidate
drifted into a preoxygenation-management task and retained unsupported alternate
strategies plus a repeated options-only cue after its single rewrite. Its
editorial pass was insufficient: the stated counterfactual did not change which
answer was correct. This is a failed candidate, not a completed quality milestone.

Contract v2 now requires an exact bounded stem substitution and a proposed
different existing key. Both the original condition and replacement must appear
in the concept-card counterfactual. The server reconstructs the changed stem
and sends only that stem and the unchanged choices to the independent blind
solver. Same-answer, ambiguous, unanchored or unrelated proposed changes fail;
unavailable or malformed verification remains pending. Expected answers are
never disclosed to the blind solver. Topic matching also becomes an explicit
part of editorial review. Guards reject references to an unspecified source in
the stem, treatment choices containing their own explanatory rationale, and
unverified dose/concentration/percentage claims in text-only MC/MS content.

The next single-question acceptance uses indexed static/dynamic compliance
passages on physical PDF pages 731–732, with respiratory-physiology objective
I.A.2. This evidence explicitly contrasts tissue/chest-wall compliance with the
airway-resistance component of dynamic compliance, allowing condition changes
to be checked against actual alternative answers. No source text or complete
generated question is included in this public report. Local targeted board tests
pass (16); the full local suite ran 866 tests with only the previously observed
PDF image-coverage fixture failure and one skip. New CI and live controls remain
required before calling the quality milestone complete.


The expanded v2 read-only control (42756829618) rejected the restatement and
trap but again exposed intermittent model acceptance of the wrong objective.
The existing conservative topic classifier now includes the official malignant
hyperthermia/myopathy heading and flags an unambiguous stem-topic conflict with
the selected objective. Ambiguous matches abstain; a matching candidate never
proves verified classification. Independent editorial review remains mandatory.
This is a reusable mismatch guard, not a forced pass for any topic.


## Verified v2 controls and CI

Source commit 28a600bcd3be6cd91450db74dc505ced1a2a6489 passed CI
42757571992: 867 Python tests (one skip), 113 Worker tests, reviewer container
build, and repository validation. Focused local checks passed 17 board-quality
tests and four existing classifier tests. Read-only live control 42757585816
flagged the old objective/counterfactual/trap defects and the second candidate's
ineffective counterfactual; deterministic checks also caught the obsolete drug,
source-dependent stem, explanatory choice and unverified concentration. The
control made no database writes and did not generate or publish a question.


Deployment 42757659182 passed container rollout and authenticated smoke checks.
Acceptance 42757994927 reached concept and draft generation, then failed at
rationale with PROVIDER_RATE_LIMIT (8,000 TPM, used 7,382, requested 4,020).
No question or resumable checkpoint was persisted for this interrupted attempt.
The relay now retains a bounded explicit provider retry interval from the
sanitized error when Retry-After is absent; the existing backend still retries
only once, only for waits up to 60 seconds. Private errors remain unlogged.
Targeted gateway tests pass (31), including missing-header, fractional-second,
millisecond and oversized-wait cases. Live recovery remains to be verified.
