# Staging generator recovery

## Verified failure

The deployed gateway version `594c6650-0bff-4667-b64e-b48dbd5b8573`
logged Cloudflare concept-card HTTP 200 followed by PROVIDER_UPSTREAM at
2026-11-09 02:56:16 UTC. This reproduces on the latest version, not only an
old rollout. The earlier `model: none` diagnostic is corrected in that version.

An isolated concept-card request used the current step contract and the eight
ranked indexed Nagelhout passages for Airway management (9,600 excerpt
characters). Qwen's default thinking exhausted all 1,200 completion tokens:
HTTP 200, finish_reason=length, no valid JSON, 58,434 ms. Low reasoning effort
alone still exhausted 1,200 tokens and returned incomplete JSON (44,044 ms).

Keeping system/user roles, requesting JSON output and setting
chat_template_kwargs.enable_thinking=false returned finish_reason=stop and
all six concept-card fields using 510 completion tokens (29,459 ms).
No incomplete output was accepted and no validation gate was relaxed.

## Baseline and scope

The legacy Supabase generate-questions implementation used one schema-constrained
Gemini request over supplied material. It is separate from the current indexed
three-stage Python pipeline. Rolling it back would not preserve later safeguards.
The latest observed saved staging draft before recovery was created at
2026-11-08 20:59:11 UTC using openai/gpt-oss-120b, topic Intubation,
status pending_review, next_state needs_editorial_review. A saved draft is not
proof that every quality gate passed.

The recovery changes Qwen request settings, records sanitized output-failure
categories, and excludes Gemini from metadata diagnostics. Existing Groq drafting,
evidence retrieval, citation reconciliation, rewrite limits, independent blind
review and unpublished persistence remain in place. Staging configuration enables
the existing one-rewrite and blind-review paths with a distinct Groq reviewer,
qwen/qwen3.8-27b. Metadata availability alone does not verify live review.

PR #169 separately rebaselines two asset budgets; it does not repair generation.

## Offline verification

- 67 Node gateway, relay and workspace tests passed.
- 15 grounded execution, 17 screened generation, 11 grounded pipeline and
  15 checkpoint-store Python tests passed.
- Repository validation and performance budgets passed.

## First live acceptance and rollout failure

PR #170 deployed Worker version bcccb569-8bee-4254-9e94-df80d77059aa.
Authenticated source integrity, evidence preflight, private draft-bank reads and
the signed container relay passed. The live concept card completed in 9,795 ms
and Groq drafting in 5,619 ms, both HTTP 200.

At 03:22:46 UTC the container was terminated during the next stage. Cloudflare
logged `Runtime signalled the container to exit due to a new version rollout`.
Its application configuration changed at 03:22:37, after deployment commands and
smoke checks had already returned. No draft was saved by that interrupted run.

The deployment now waits before authenticated warmup: at least 90 seconds since
the gate began, at least 60 seconds since the last application configuration
update, no active rollout/errors, and no old running image or transitional
instance state. The bounded gate blocks paid acceptance if these conditions do
not settle. Four offline regressions cover the early-ready window, old image,
active rollout and invalid metadata. This is a settling criterion, not a claim
that Wrangler itself waits for container replacement.

## Groq drafting output budget

The settling gate passed and authenticated smoke succeeded on version
e910f323-1b49-441c-b381-16e485cb809c. The second acceptance stayed up but failed
at item_draft with PROVIDER_RESPONSE after Groq HTTP 200.

An isolated request through the signed internal relay reproduced GPT-OSS
finish_reason=length, exactly 2,600 completion tokens, and invalid JSON
(6,083 ms). A second immediate request received an explicit rate-limit response;
it was not silently retried. A later candidate-only probe using JSON-object mode
and low reasoning effort passed with all four options and their evidence-map
entries, finish_reason=stop, 1,100 completion tokens, and valid JSON (2,931 ms).
The token budget stayed at 2,600.

The gateway now applies those verified settings to Groq GPT-OSS generation and
rewrite requests, requests JSON for the distinct Groq Qwen reviewer, and rejects
truncated Groq output before it becomes an ambiguous Python parsing failure.
The diagnostic probes do not run rationale, screening, persistence or publication.

## Rationale deadline

After the Groq fix, live concept-card generation and drafting succeeded again;
drafting completed in 2,987 ms. Rationale generation exceeded the Python relay's
50-second deadline and returned PROVIDER_TIMEOUT with failed_step=rationale.
No draft was saved.

The rationale contract now specifies the exact flat object shape and concise
one- or two-sentence explanations for each field/choice. It prohibits repeating
the draft and source excerpts in the response, while retaining mechanism,
stem-context, affirmative-evidence, ambiguity and no-invented-citation requirements.
An isolated signed-relay rationale probe passed all four fields and all four
choice explanations in 9,923 ms. The drafting input for that probe completed in
2,872 ms with 1,091 tokens. No rationale timeout was extended and no evidence or
validation requirement was removed.

## Citation and guarded rewrite recovery

The next live run completed generation and saved a pending_review draft, but
quality validation correctly rejected fabricated/reformatted quotations and
empty citation entries. The attempted correction was also rejected because the
provider returned a rewrite envelope rather than top-level canonical fields.
This draft remains flagged and unpublished; it is not a successful quality result.

The final quality batch:

- Materializes quotations and omitted option-reference citations only from known
  indexed passage identities and physical page bindings. Unknown references,
  wrong supplied identities/pages and supplied false quotations still fail.
- Supplies trusted cited-source text to the existing single rewrite, without
  duplicating the same text in its original-item prompt.
- Requires all canonical item fields and exact protected metadata. Recognized
  rewrite envelopes are unwrapped only with validated protocol/request fields;
  candidate metadata and answer protections remain unchanged afterward.
- Allows one bounded wait only for an explicit provider 429 with Retry-After
  between 1 and 60 seconds; ambiguous failures are never retried.
- Passes the selected topic through all generation stages. Previously the topic
  selected retrieval but was omitted from model requests.
- Uses the existing physical page filter for a controlled obesity/FRC/oxygen
  consumption acceptance question, supported by one coherent indexed paragraph.
- Reports an already-saved generated draft truthfully in the UI and disables
  the extra Save action, avoiding a duplicate draft.

An isolated signed-relay quality probe passed schema, deterministic_text, math,
evidence and blind_model on 2026-11-09 at 04:19:55 UTC, with zero generator issues
and zero rewrite attempts. Drafting took 2,432 ms and rationale took 6,957 ms.
The test reused already-produced model responses to isolate screening and did
not save or publish a question. Duplicate screening, independent clinical option
adjudication and human review remain explicitly pending, not implicitly passed.

## Clinical ambiguity found despite automated passes

The next authenticated live run saved a pending-review question and passed the
automated gates, but source comparison found a second true answer. The source
states that both decreased FRC and increased oxygen consumption contribute; the
generated rationale invented a primary/secondary ranking to dismiss one of them.
That result is not accepted as a successful high-quality recovery question.

The next batch rejects unsupported source-ranking arguments and instructs blind
MC review to return every defensible answer, even when more than one is correct.
Existing scoring flags that disagreement. The drafting contract directs questions
about combined mechanisms to use parallel combinations rather than invent a
ranking. Earlier failed recovery drafts are marked needs_revision by automated
defect reports, with no human clinical approval or publication.

The isolated revised quality probe passed all required automated gates. Semantic
duplicate coverage, independent clinical option adjudication and human review
still remain pending and cannot be implied by these passes. At this point,
final authenticated generation, source comparison and persistence were still
unverified; the final result is recorded below.

## Final deployment and verification-state correction

The recovery deployment at a28bfac was blocked before AI calls when an idle
container left Cloudflare's rollout progressing for more than four minutes.
PR #176 adds the existing authenticated read-only diagnostic as a warmup, while
retaining the mandatory rollout gate and final authenticated smoke. The following
rollout settled successfully and source/PDF/page integrity, indexed preflight,
private drafts, anonymous-access rejection and signed relay checks passed.

The next generation correctly failed schema because a model placed a numeric
verification flag inside a citation and omitted the required item-level flag.
PR #177 makes the text-only stage own the false page-image verification state,
removes unsupported citation-level assertions, and protects the state during
rewrites. Three negative regressions passed. No page image or clinical value is
claimed verified by this operation. A later draft was also correctly rejected
when its rewrite dropped required option error-pattern tags. These failed drafts
remain unpublished and are marked needs_revision by automated QA, never approved.

The final functional source commit is 8cb7ac8ed0654b32e1741958cb46c948b5f09884.
Its staging Worker version is 71945cc1-00d0-4259-8834-df7b1b2ea261 at 100% traffic.
The regression run completed 806 Python tests (one skipped) and all 104 Node tests.
Main architecture, content integrity, budgets, all four browser regression groups,
and the verified-site deployment passed:
https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42565627461

PR #178 adds a separately confirmed acceptance workflow against the settled
existing deployment, avoiding a rebuild for each verification. Ordinary main
pushes never generate questions through that workflow. A verbose acceptance topic
returned NO_INDEXED_EVIDENCE before paid calls; using the actual indexed terms
preserved retrieval/index behavior and allowed the focused obesity test to proceed. Its unsupported distractors were
correctly rejected after the single allowed rewrite; no quality gate was bypassed.
The final acceptance therefore uses a source table that explicitly supplies both
triggering and nontriggering categories, instead of a paragraph that cannot
adjudicate unrelated mechanisms. PR #178 also strengthens the existing draft/
rewrite instructions for source-refuted parallel mechanisms and required option
fields. It does not guarantee all generated questions will pass.

## Verified end-to-end result — 2026-11-09 05:16 UTC

**One authenticated indexed generation completed and was saved unpublished.**
This verifies the pipeline and a controlled recall item; it is not clinical
approval or a guarantee of arbitrary-topic question quality.

- Acceptance run: https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/42566146423
- Draft ID: `e9ee3c59-0924-402c-9501-63464d53ffdb`.
- Database status: `pending_review`; API `published=false`,
  screening `can_publish=false`; reviewed_by and reviewed_at remain null.
- Book: `Nagelhout__Elisha_.pdf`, textbook
  `6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d`, still ready, 1,660 physical PDF pages.
- Source: physical PDF page 984, Box 36.9, passage
  `ac27bdb7-a2ae-4482-ba62-82b3ece25e16`.
- Topic: malignant hyperthermia triggering/nontriggering agents.
- Generator: Groq `openai/gpt-oss-120b`; independent blind reviewer:
  Groq `qwen/qwen3.8-27b`. Concept/rationale use Cloudflare Qwen.
- One automatic rewrite corrected error-pattern descriptions under R-6.3.
  No generator issues remained after the rewrite.
- Exactly one new draft exists for the acceptance-run time window.
- Textbook identity, physical page binding and verbatim excerpt equality were
  independently confirmed against the existing indexed passage.
- The question key (desflurane) and the local-anesthetic, nitrous-oxide and opioid
  distractor categories agree with the source table. The item is recall-level.

| Check | Verified status |
| --- | --- |
| Schema | pass |
| Deterministic wording | pass |
| Math | pass |
| Evidence validation | pass |
| Distinct-model blind review | pass |
| Semantic duplicates | pending — semantic index not supplied |
| Independent option evidence adjudication | pending — retrieved passages still need clinical adjudication |
| Human clinical/blueprint review | pending |
| Publication | blocked |

The concept-card relevance includes a broader statement about triggering agents
being stocked in an operating room that the cited table does not establish.
An automated QA note explicitly records this for correction/review; it is not
human approval. The generated question and screening output were not edited to
make the acceptance pass. Page-image/numeric verification remains false.

All six earlier defective recovery drafts remain unpublished with needs_revision:
`eec2209c-419d-40ea-b830-6586d2b06125`,
`d87e0523-a4bd-40a9-8f61-cdaabd6ad297`,
`038defcb-295a-43a9-bdb4-5bb6a310b183`,
`11d8fe2a-af0c-4986-ab17-f1524eb2fe1a`,
`273d8969-5957-4aec-9c4d-7c46548de822`, and
`217c7f66-65ff-4c4a-849a-09598f6c26c1`.

Gemini remains excluded from active routing and readiness checks. Existing
textbook/index data, validation gates and independent review functionality were
preserved. No question was published. The final report and already-tested
acceptance fixture update do not redeploy the functional Worker or run another
paid generation.

## Follow-up: independent source review and versioned concept correction

The independent option-review modules existed but were not passed from the live
CLI into the indexed pipeline, and their report was not attached to screening.
The follow-up connects that existing handoff through a separate staging opt-in,
a distinct reviewer-model relay step, and persisted screening results. The
reviewer receives no answer key, generator rationale, expected verdicts or error
patterns. Each option must cite independently retrieved passages and supply a
verbatim quote; unsupported quotes, contradiction, source silence, missing
retrieval and invalid provider output keep the stage pending. Human clinical
review and publication remain blocked even when model adjudication completes.

Per-option retrieval now searches the option text OR the selected topic within
the same authenticated owner's textbook. This can retrieve both a drug's class
and the clinical classification table; neither the answer key nor generator
citations seed that independent search. Existing textbook content and indexing
are unchanged.

The immutable draft-revision path permits only a bounded concept-card relevance
text correction. It cannot change concept evidence IDs, the answer key, identity,
review status or publication state. The live acceptance checks will append and
verify the known relevance correction without modifying the original draft, then
verify a fresh source-reviewed unpublished generation.

The canonical inventory audit currently reports 9,000 unique questions across 21
sources, digest 44e9be2173cac71a71f51e3cfe48b3712d3ad301e8d076f01796a3aee50497a5.
The staging question_semantic_index_v2 table is absent; its existing embedding
bridge only accepts Gemini. No Gemini calls, schema changes or partial-index
clearance were enabled. A complete non-Gemini index remains a separate unfinished
requirement; semantic duplicate status stays pending.

Verification of the new deployed reviewer step and versioned saved-draft
correction is pending. The prior verified result above remains historical.

### Follow-up live result and rationale routing

PR #179 passed CI: 817 Python tests (one skipped) and 105 Node tests. The
new staging image passed rollout, authenticated integrity and preflight checks.
At 08:51 AM Eastern on November 9 the acceptance successfully appended revision
ca4487c0-146a-4278-b643-7f403420ef49 for draft
e9ee3c59-0924-402c-9501-63464d53ffdb. Its corrected relevance, unchanged key and
unchanged evidence were read back; the original generated question is retained.
No clinical approval or publication was performed.

The subsequent fresh generation timed out at the Cloudflare rationale step
before reaching independent option review (PROVIDER_TIMEOUT). Therefore the new
live option reviewer is not yet verified by that run. A routing correction sends
rationale writing to the existing Groq JSON/low-effort path, while Cloudflare
retains concept-card generation and the distinct Qwen reviewer retains both
review tasks. The 50-second deadline and rationale output limit are unchanged.
The changed-route regression passes; final live verification is still required.

The live API remains single-question and single-selected-textbook. It does not
currently implement cross-textbook corroboration or queued 25-question batches.
Only controlled recall MC generation has been verified; consistent application/
analysis quality and multiple formats have not been established by a mixed pilot.

### Cloudflare concept latency and Groq-only authoring

The PR #180 deployment and authenticated smoke passed, but its fresh run timed
out at concept_card before rationale (09:01 AM Eastern on November 9). No new
draft was saved by that interrupted request. This confirms that authoring latency
is not confined to the Cloudflare rationale step.

The next configuration disables AI_HYBRID_ENABLED for this staging recovery path,
using the already implemented Groq route for concept, draft and rationale. The
separate Qwen model still performs both answer-blind and indexed-source option
reviews through Groq. No timeout, output cap, validation rule or approval state
is relaxed. Cloudflare remains the hosting/gateway/container platform; Cloudflare
AI authoring is explicitly disabled. Metadata diagnostics report the disabled
provider without making a request to it, and only enabled providers gate metadata
readiness. Gemini remains disabled.

### Full Groq-mode run and independent review protocol clarification

The Groq-only deployment passed authenticated smoke. Its fresh generation and
independent source review completed in about 23 seconds, saving unpublished draft
bb4d1576-3ca2-4c7d-b539-56520e861957 at 09:09 AM Eastern. Schema, math, evidence
and answer-blind checks passed. The acceptance did not pass: answer length was
flagged, and independent source adjudication remained pending. This draft is not
accepted as ready for use.

The live reviewer correctly refuted the false choices, but interpreted the old
contradiction_found field as contradiction between evidence and a false option.
The evaluator intended source conflict, so the response contract now names it
source_conflict_found and explicitly distinguishes expected refutation from
unresolved conflicting evidence. The existing evaluator is adapted internally;
conflicting sources still block completion. The reviewer also assembled table
headings and separated entries into non-verbatim quotations, which were correctly
rejected. It now returns separate short quotes, each independently required to
occur verbatim in a cited indexed excerpt. No synthetic table quotation is
accepted.

The one rewrite had been spent on initial citation issues before answer-length
screening ran. Inexpensive wording checks now join the initial rewrite's issue
list, and its corrected output is checked for those issues too. This preserves
the one-attempt cap, protected key/text, and the existing wording threshold.
Negative tests cover synthesized quotes and the single-rewrite issue union.
No cross-book search or bulk generation was enabled by these corrections.

### Bounded independent review context and explicit rate-limit handling

PR #182's live generation completed in about six seconds and saved draft
83916827-3192-45ab-806e-c81e2f26ba04. Schema, wording, math, evidence and answer-blind
checks passed without a rewrite. Source adjudication remained pending because
Groq returned an explicit 429, verified in sanitized relay telemetry. This is not
reported as a completed verification. Manual inspection also found background
mechanistic claims beyond the supplied classification table, so it is not the
final accepted question.

Independent retrieval now keeps the highest-ranked option-classification passage
and a separately retrieved topic passage, rather than sending many OR-ranked
matches. The topic query is cached within the request. All searches remain scoped
to the authenticated owner's selected textbook. The live MH table was verified as
the top result for the topic, while drug-class searches supply the other pages.
Required quote validation, full option coverage, source-conflict handling and
human-review gates are unchanged. Failed searches remain pending.

The reviewer now shares the rewrite's bounded handling for explicit 429 responses:
wait once only with server Retry-After of 1–60 seconds, then retry the declined
request once. Ambiguous timeouts, missing/oversized delays and second failures
are not retried. Sanitized provider categories persist when review cannot finish.
Tests verify bounded attempts, no timeout retries and independently retrieved
classification/topic provenance. Authoring instructions also explicitly limit
background claims to supplied evidence and distinguish factual recall from an
actual clinical crisis.

The user has deferred larger batches and cross-textbook sourcing. The current
stop condition is one nice, source-supported unpublished question completing the
automated generation/verification/repair/recheck cycle. Full semantic duplicate
coverage and human approval remain outside that stop condition and stay pending.

### Server-owned blind-review correlation

The settled-image run generated draft 56636be0-5655-43f4-b7a8-543d59323521 with
schema, wording, math and evidence passes. Its factual drug-classification stem
and choices were source-supported, with recall/crisis labels consistent with the
item. Blind review reported a missing/mismatched echoed item ID, which is a
protocol problem rather than an answer disagreement. It is not reported as a
completed cycle.

The authenticated adapter now keeps the internal question ID out of the model
prompt and binds the single awaited response to the trusted request on the
server. The independent answer field is never supplied by the generator or
corrected by this binding. Missing/invalid answer structures and explicit wrong
model-supplied IDs are rejected; a valid but incorrect choice still fails the
unchanged answer comparator. Protocol failures remain pending rather than
spending an editorial rewrite on a question whose content is not the problem.
Regression tests cover wrong-answer preservation, explicit ID mismatch, answer
shape/type checks, lack of ID/key leakage, and all five response formats.


### Source-review request budget and exact quote restoration

PR185 passed staging CI and deployed successfully in run 42642259011, including
settled-container and authenticated smoke verification. Its bounded diagnostic
records quota categories and numeric counters without provider messages or book
text. Fractional Retry-After values round up for the existing single retry.

Isolated source review (run 42642486597) used five indexed passages and 9,221
request characters, without creating or changing drafts. The provider rejected
it with tokens-per-minute limit 1,000 and requested 1,520, despite headers showing
8,000 remaining tokens. Reducing only the completion ceiling from 1,800 to 1,000
allowed the same packet through (run 42642658292). The resulting review correctly
remained pending because a quotation was not verbatim.

A second diagnostic (run 42642973054) confirmed that the invalid quotations were
neither exact, Unicode-compatible, nor merely whitespace variants. Validation
was therefore not relaxed. The adapter now asks the independent model to select
short source-span IDs, then copies the exact, contiguous indexed substrings on
the trusted server. Unknown, cross-option or uncited references are rejected;
independent verdicts remain unchanged and the existing exact-quote check still
runs. No expected answer or generator rationale enters source review. The source
review completion ceiling is 1,000 and explanations are concise. Tests cover
wrong-verdict preservation, exact raw ligature restoration, citation boundaries,
immutable inputs and bounded output. Live acceptance remains to be run.


### Full live generation and final editorial source check

Deployment/acceptance run 42643815422 passed. It generated exactly one draft,
167026ce-7c1c-489f-8c4b-28255ac78ef8, with schema, deterministic wording, math,
evidence, blind-answer and independent option-source checks passing; there were
zero generator issues and no rewrite was needed. The result remained unpublished,
pending human review and semantic duplicate verification.

Manual review of the saved question found source-only limitations beyond those
automated checks: the concept card supplied receptor physiology absent from its
classification excerpt, and the rationale generalized the listed depolarizing
agent to an overly broad exclusive class claim. The stem, choices, key and
independent source judgments are supported. This is not yet reported as a fully
finished question. The existing append-only revision proposal now permits bounded
corrections to existing concept explanation and rationale text. Citation IDs,
blueprint identity, answers and verification/publication flags remain protected;
all existing source/schema validation and human-review requirements still apply.
