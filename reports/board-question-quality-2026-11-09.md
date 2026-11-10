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


Acceptance 42758690112 verified relay extraction of a 25-second provider delay
but still returned 429: initial authoring bypassed the bounded helper already
used by rewrite and reviews. All three authoring stages now receive that same
helper through the callback passed to the pipeline. The handoff regression test
invokes the actual callback for concept, draft and rationale, confirms exactly
one retry and a bounded wait for each. No quality rules were relaxed.


Acceptance 42759379255 verified successful rate-limit recovery and persisted
draft 5cdb6e33-d6f5-426a-9fd2-42e88dd597ad, but rejected it after one rewrite.
It remained a recall task; its counterfactual left contradictory diagnostic
qualifiers and the independent solver retained the old answer. A worded formula
also reversed the ratio in interleaved source text, while explanation review
remained pending. This is another failed candidate, not successful acceptance.
New authoring instructions require interpreting multiple relevant findings or
affected/unaffected components and omit unverified MC/MS equations. A deterministic
page-image guard now includes equations written as divided/multiplied by. The
next request caps retrieval at two already indexed relevant passages; indexing
and evidence validation remain unchanged.


Deployment/acceptance 42760003431 saved but rejected draft
478fd4be-b899-41ec-8c71-2d470feba9b5. Its changed condition still did not produce
a demonstrated unique answer; explanation review hit its existing output cap.
Source review now supports bounded six-field batches with exact per-batch field
coverage and unchanged global source/span/citation checks. Any missing, swapped
or invalid response remains pending; no partial batch can pass the whole item.
Provider output limits and independent model identity are unchanged. Initial
planning now explicitly pairs two physiological components with the original and
alternative source-supported conditions.


## Recovery after execution workspace failure

The latest source CI (42760800256) passed. Deployment 42760821633 completed
rollout and authenticated smoke successfully; the combined run failed at paid
acceptance, preserving unpublished draft dd641cda-00c4-49b9-9fdf-5ce19620fb9b.
That candidate still failed application-level reasoning, meaningful counterfactual
and affirmative distractor support. It is not an accepted quality milestone.
A read-only reproduction of the existing ranked query showed that the two-result
cap selected only static-compliance passages. The next acceptance request restores
the explicit dynamic/static topic and allows all four matching passages on the
same two indexed pages. This supplies the missing contrast without changing
indexing, search ranking, source validation, models or the one-rewrite limit.
The execution workspace failed to recover; subsequent work uses the connected
repository and staging services. Live acceptance is still required.


Acceptance 42764346220 stopped at rationale with PROVIDER_RATE_LIMIT and saved
no draft or checkpoint. Sanitized telemetry showed the same request's estimate
rose from 4,104 to 4,740 tokens between attempts: the 34-second first wait left
4,548 tokens available and the second attempt needed another two seconds.
The one allowed explicit-429 retry now waits a full bounded 60-second TPM
window; it never adds a third attempt or retries ambiguous transport failures.
The corrected exact dynamic/static query ranks the two required passages first,
so acceptance uses those two rather than four. This reduces payload while
retaining both physiological definitions. New CI and live acceptance required.


CI 42765078712 passed 869 Python tests (one skip), 114 Worker tests, the
container build and repository validation. Deployment 42764841722 and its
authenticated smoke passed. Acceptance 42765180944 verified rate-limit recovery
and saved unpublished df490c7f-4a85-4eb8-9b97-740b2a2910bc, but the candidate
still failed blind agreement, affirmative source support and the counterfactual.
It is not accepted. Direct inspection also found simple recall disguised as a
case and unsupported clinical statements which a source-review pass alone would
not establish as correct.

The authoring adapter previously placed its trusted server-written step contract
inside the same user JSON as indexed text and model-written cards. Move only
the fixed step instructions to the system role, preserving all source/model
content as untrusted user data. A transport-boundary regression checks all three
authoring stages and ensures evidence and model content never gain system
priority. This addresses instruction placement, not proven generation quality;
CI and a fresh live candidate must still demonstrate the result.


CI 42765929647 and deployment 42765949990 passed, but instruction-placement
acceptance 42766355689 rejected unpublished e530328c-3266-4671-b12b-df732b5c783b.
The experiment did not improve quality and is reverted. The relay had forced
GPT-OSS authoring to low reasoning effort. Test the documented medium effort
only for the same generator's concept/draft/rationale/rewrite steps; source,
blind, editorial and options-only models/settings remain unchanged. Token caps,
all validators and the single protected rewrite remain unchanged. No successful
quality milestone is claimed. Official provider reference:
https://console.groq.com/docs/reasoning (GPT-OSS supports low, medium and high).


Medium-effort CI 42767185814 and deployment 42767204294 passed. Acceptance
42767615194 saved unpublished 782dcc83-a42c-432f-9864-8578ad0ea84e but failed
the anchored counterfactual. Direct inspection found an implausible disease
transition rather than a stable case and a reversed authored equation missed
by source review. Extend the existing page-image guard to calculated-as/from/by
and slash notation, covered by the observed failing claims. Clarify that a
counterfactual is a separate hypothetical, not the original stem, and that a
component-comparison topic requires the same two components in all choices.
No gate was relaxed; this candidate is not a successful quality milestone.


CI 42768488073 and deployment 42768508986 passed. Acceptance 42768901745
stopped at concept_card with a provider HTTP 400 request rejection before any
draft. Existing sanitization did not expose the provider's machine error code.
Add bounded diagnostic extraction of fixed known error codes/parameter names
only; raw error messages, failed generations and source text remain excluded.
This does not retry the rejection or change generation/quality behavior.


CI 42769394678 and deployment 42769390772 passed. Acceptance 42769803215
passed authoring but exceeded the client's four-minute wait. Read-only database
verification found exactly the saved candidate d9da16d9-6134-4688-b033-82debbfd0abe;
it still failed the counterfactual and page-image equation guard, so no retry of
that request or quality success is claimed. Container packaging and the protected
rewrite handoff were inspected and preserve the intended path and key safety.
Test high effort for generator authoring only, with bounded response ceilings
2,400 concept / 3,500 draft / 2,400 rationale / unchanged 3,500 rewrite tokens, while keeping
independent reviewer settings unchanged. Allow the explicit acceptance client up
to eight minutes for a single call under observed per-minute review limits; no
extra request or quality bypass is introduced. Fresh CI and acceptance required.


CI 42770912338 and deployment 42770930756 passed. Acceptance 42771325499
failed at concept_card before persistence. The new safe diagnostic identified
provider_error_code=json_validate_failed (HTTP 400), rather than authentication,
model availability or an unsupported reasoning parameter. Test a larger bounded
4,096-token planning response and keep high effort only for that planning step;
draft, rationale and protected rewrite use medium effort. Independent reviewers
retain their original settings. This is a configuration experiment, not evidence
that question quality has been solved. CI and fresh acceptance remain required.


Code-path inspection found that the concept-card request passed format=null,
although generate_one already knew the selected format. Pass that format through
to planning, so format-conditional writing/page-image instructions have the same
context in all three authoring calls. Existing runner adapters now assert the
actual request format. Authoring contract v3 is returned by preflight and bound
into the checkpoint fingerprint so pre-fix checkpoints cannot be reused under
the changed planning contract. Acceptance requires v3 before spending a call.
CI 42771750672 passed before this context fix; fresh validation is required.


## Version verified; finish counterfactuals after drafting and isolate citation scopes

Diagnostic deployment 42826187692 verified both the container contents and the
authenticated runtime authoring contract v3 without AI calls. The version mismatch
is resolved; it must not be bypassed in future acceptance. The subsequent live
run (42772563420, job 129865907771) saved unpublished draft
49551d1a-01a6-483a-b9e6-59c892a01ad9 but failed counterfactual screening and left
source review pending because grouped fields had incompatible allowed citations.
This is not a successful question-quality milestone.

Partition independent source-review batches by their identical allowed source
sets, retaining exact full-field coverage, source-span verification and rejection
of uncited support. Let the existing rationale call finalize a bounded condition
substitution against the actual draft; the server records this teaching proposal
without changing stem, options, key or evidence. Existing separate editorial and
blind changed-stem checks must still prove a different unique answer. Missing or
invalid proposals do not grant a pass. No extra authoring call or second rewrite
is introduced. Extend the existing text-only numerical guard to authored pressure
values, including Unicode units; indexed passages remain untouched.

Authoring contract v4 prevents reuse of v3 checkpoints. Add authenticated read-only
runtime-version verification to the staging deployment before paid acceptance.
Larger batches, cross-textbook sourcing and production deployment remain deferred.


CI 42829268305 passed all 872 Python tests (one skip), 116 Worker tests,
container build and repository validation. Deployment uploaded the new image;
its final read-only smoke had ECONNRESET. Standalone acceptance 42829903998
then passed authentication, source/PDF/page integrity, boundaries, indexed
preflight and provider checks, but concept generation was rejected with
json_validate_failed before a draft. No quality success is claimed. The existing
GPT-OSS concept card now uses documented strict JSON-schema output with exactly
the same six canonical fields; all server/source/independent validation remains
mandatory. Other model steps retain their existing formats and identities.
Provider reference: https://console.groq.com/docs/structured-outputs.


Strict-output CI 42830794116 and deployment 42830827655 passed, including
live v4 verification. Acceptance 42831453480 passed read-only smoke but concept
JSON was again rejected before a draft. Cloudflare's deployed Worker content
was inspected for the strict schema name and response type; the intended code
was present. Restore medium planning effort (which previously produced valid
concept objects), retaining strict six-field shape and finished-stem finalization.
Fixed diagnostic categories now distinguish invalid JSON from other JSON shapes
and record only bounded character counts; no failed text or reasoning is logged.
All 34 focused relay tests pass. No successful quality milestone is claimed yet.


Medium-effort strict-output CI 42832359944 and deployment 42832406927 passed.
Acceptance 42833139010 completed source review with four citation-scope batches
and saved unpublished 34c128dd-8586-47f8-b7bd-1a8af8d6d2e4. It still failed
clinical uniqueness, reasoning level, equation/wording and counterfactual checks.
The model omitted the new rationale proposal field, so legacy planning text
remained; no successful milestone is claimed.

For live MC/MS rationale calls, a strict schema now requires the bounded-edit
proposal and explanations for every existing choice. Independent changed-stem
verification still must prove a different unique answer; the author proposal
never grants a pass. Source review also flags explicit absence-as-disproof
reasoning even if the model says it is supported. Give qualitative text-only
and applied-case requirements system priority without promoting source text or
model content. The existing single rewrite gets an explicit R-8.5 correction
instruction. Authoring contract v5 invalidates earlier checkpoints.
Focused source-review and relay checks pass (15 and 35 tests). The full local
suite ran 873 tests with one skip and only the known local PyMuPDF fixture
failure. New CI and live acceptance are required before claiming completion.


V5 CI 42835089302 and deployment 42835085517 passed. Acceptance
42835822707 lost its client connection, but read-only database inspection
confirmed an unpublished candidate was saved. The changed-stem blind check
correctly found three answers, and the item retained an answer cue after its
one rewrite. This is a rejected candidate, not a completed quality milestone.

V6 adds a private MC choice plan within the existing concept call. It requires
four distinct two-component response patterns, preserves those exact choices
in the draft, and binds the final counterfactual to the planned stem edit. The
plan never becomes clinical evidence or a saved question field. Independent
source, blind, editorial and changed-stem reviews still determine their own
results. Source review checks the clinical premises of a server-rendered
counterfactual; the separate changed-stem blind check verifies the option mapping.
No extra model stage, textbook indexing change, or Gemini activation is added.
Explicit fractional retry intervals accept up to 20 decimal places while
preserving the existing bounded rate-limit wait. Focused planning (2), source
review (16), and relay (36) tests pass. The full local suite ran 876 tests with
one skip and only the previously identified local PyMuPDF overlap fixture failure.
CI, deployment and a fresh live question remain required.


V6 CI 42839845491 passed 876 Python tests (one skipped), 119 Node tests,
container build and repository validation. Deployment 42839871179 passed
authenticated smoke and the live v6 assertion. Acceptance 42840537365 stopped
before drafting with CONCEPT_CARD_VALIDATION after a valid provider JSON response.
No draft was saved. Add exact allowlisted planning-invariant diagnostics so the
next result identifies the actual defect without exposing generated/source text.
No clinical or structural requirement is loosened by this diagnostic change.


Diagnostic CI 42841505628 passed. Normal deployment 42841493659 built
image c9bc9166 but its rollout did not settle. An explicit staging rollout
08a787b7-5f18-4c6c-a652-2e50f32133ee selected that exact image and reached
healthy state. Acceptance 42842587812 passed all read-only boundaries but again
stopped before drafting; its validation detail was unclassified. V7 now pins
the authenticated runtime contract before any new generation, includes a fixed
validation-response contract, and covers every known concept validation category.
No candidate was saved and no clinical requirement was relaxed.


Read-only isolated concept diagnostic 42843871130 confirmed the actual defect:
all four choices and state-pair shapes were valid, objective and source IDs
matched, but original-context distractor annotations were missing. V8 removes
that duplicate annotation requirement from the PRIVATE plan, which now contains
only IDs, text and component states. The existing draft stage still must supply
null for the original key and a specific error pattern for all three distractors,
including the alternative-case key. Canonical schema and quality checks remain
unchanged. Planning still binds exact choice text and original/alternative keys;
no clinical evidence or correctness requirement is waived.

Canonical MC validation now explicitly rejects null or empty non-key learner-error
tags under R-6.3; presence alone previously let null values through. Regression
coverage confirms the private plan omits these tags while the final MC requires
them. Existing treatment of legacy keyed metadata and other formats is preserved.


V8 CI 42844619442 and deployment 42844426610 passed, including live v8
verification and local architecture/performance budgets. Acceptance 42844916356
passed concept planning and drafting (the bounded 429 retry recovered); rationale
then failed provider strict-output validation before a question was saved.

V9 uses the already server-bound MC plan as the counterfactual; its rationale call
returns only the four canonical explanation fields. It cannot change the stem,
choices or planned edit. MS and legacy no-plan rationale contracts are preserved.
The independent changed-stem and source-premise checks remain mandatory. Enable
the existing owner/request/evidence-bound staging checkpoint store, and expose
only the request UUID in acceptance logs. Completed-result recovery requires
preflight proof of completion and uses the same request, without another AI call.
