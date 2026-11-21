# MC runtime reliability — 18 November 2026

Scope: staging MC generator only, `fix/board-question-quality`. No production/main/PR #189 promotion, question publication, bank rebuild or embedding backfill.

## Demonstrated failure and correction

The connected container logs at 2026-11-17 23:10:41 UTC report that Gunicorn worker PID 2 was sent SIGKILL, with its out-of-memory diagnostic, immediately before the non-JSON backend 500. This supports memory exhaustion as a cause; a kernel OOM record was not available. Inspection found that semantic screening accumulated all 9,000 Python float-vector lists, then made another neighbor-list copy. A rewrite can recursively scan again while the preceding vectors remain in scope. The previous acceptance runner could also start the next question after a client disconnect while backend work remained active.

The scanner now packs each page's validated vector into double-precision `array('d')` storage immediately, preserving all values, all canonical IDs/hashes, full coverage checks and the existing cosine threshold. It does not omit neighbors, approximate scores or claim completeness for a partial index. There are no bank/index writes and no additional model calls.

Synthetic 9,000 × 1,024-vector process benchmark:

| Implementation | Peak RSS | Time | Matches |
| --- | ---: | ---: | ---: |
| Previous | 443.3 MiB | 6.40 s | 448 |
| Compact doubles | 155.4 MiB | 6.11 s | 448 |

The ordered match/score JSON hashes were identical: `ca91b42d3106d970b12ef1faebc1dc72abc26fa91e6d2fa8863c79d511573ffd`. This is a memory/equivalence benchmark, not clinical acceptance or an assertion that live OOM recovery has passed.

## Durable generation and rewrite accounting

The private staging table `generation_attempts_v2` records an owner/item admission before the first paid call. The owner/item key has no expiration; changed evidence, request hash, model or authoring-contract version cannot spend the same item ID again. The one rewrite is atomically reserved and committed before the provider call, including ambiguous failures. Only a previously completed checkpoint can recover without authoring or review resampling. Any incomplete checkpoint is explicitly blocked from replay.

A nonblocking process lock serializes paid generation across the staging reviewer's HTTP threads. This relies on the existing one-worker, one-container staging deployment; it is not a distributed queue. Durable item receipts still protect the same item across process restarts. The lock deliberately avoids PostgreSQL session advisory locks, which would be unsafe on transaction-pooling connections.

The table has RLS enabled and no `anon`/`authenticated` access. Admission checks the owned, ready textbook before reserving an item. Historical book IDs have no foreign-key dependency, so deleting a book cannot reset an item budget or be blocked by a receipt. Existing saved UUID items and the two known ambiguous partial attempts were conservatively blocked (53 legacy receipts). No saved question or clinical review was modified. Unknown historical item IDs that were never persisted are not reconstructable; do not manually reuse older failed IDs.

## Client transport

The Node acceptance client uses a bounded HTTPS request with the caller's explicit signal and no implicit fetch header deadline. It rejects redirects, unexpected hosts/methods and oversized responses, and performs no automatic retry. The earlier five-minute failure remains consistent with an implicit header deadline, but its original cause code was not captured; this is a correction to that exposure, not proof of its historic cause. Browser generation behavior and completed-only recovery remain intact.

## Validation before live deployment

- 1,080 Python tests ran; four skipped.
- 207 Node checks passed, including delayed headers, deadline/redirect/size rejection and warm-up-only behavior.
- Repository validation and diff checks passed.
- Staging-only schema applied and RLS/public-access boundaries verified.
- A disposable real-PostgreSQL concurrency/interruption test is prepared; it makes zero AI calls and writes no questions. Live outcome is pending.

No new clinical question has been accepted by this batch yet. The two prior 10/10 unpublished drafts remain the accepted automated examples, pending human clinical review. Live validation will first confirm the database safety boundary and exact deployed container, then use bounded fresh MC requests against the demonstrated runtime correction. Existing failed requests will not be resumed.

## Live runtime verification

Run [44288292292](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44288292292) passed the disposable real-PostgreSQL admission/budget checks, then generated exactly two fresh candidates against application `cb7cac08963165953f9d002c299e9b39cdcfd510`. Build `579e4c8d-e021-447a-af10-b002d29e0e09` succeeded; image `b852b5f94726d571cd51ce5b6210ba612a13017a74058608f6774964c1b110a8` was verified settled before generation.

Both requests completed and saved without disconnect or backend 500. Their durable ledger rows are `completed`, with one rewrite reserved each. Backend generation durations were 329 and 410 seconds, both beyond the old approximately five-minute client failure. Cloudflare container metrics peaked at 389,763,072 bytes (~372 MiB) during the run, compared with 1,187,041,280 bytes (~1,132 MiB) immediately before the prior SIGKILL. Metrics are operational observations, not clinical acceptance.

| Requested target | Saved draft | Checks | Disposition |
| --- | --- | --- | --- |
| Oxygen pressure failure | `76e7c70b-1f52-40f9-bff6-76832dd40407` | 7/10 | Held: R-6.10 absolute wording, R-2.4 explanatory support; option review correctly pending |
| Shunt/dead-space lecture | `ffe53be0-88e1-4831-84ef-4aa4e7212f53` | 8/10 | Held: R-1.3 wrong topic and R-5.3 counterfactual; actual topic was simulation education, so this is NOT respiratory clinical acceptance |

Neither draft is approved or published. No second rewrite or judgment resampling was performed. The equipment source issue concerns the scope/wording of the oxygen-analyzer explanation. Its cited excerpt contains downstream-monitor language; do not assume the source is absent or override the independent hold. Diagnose the precise claim/quote interpretation before changing that gate.

### Demonstrated lecture routing defect

The saved respiratory request actually had `topic='Learning objectives'`: the parser treated `# Learning objectives` as a clinical heading and ignored its following objective bullet. Its generic search found simulation-training content, which the author followed. Independent blueprint review correctly rejected the resulting question. The earlier ordered-objective work did not cover a Markdown heading with no colon.

The correction recognizes objective headers after removing Markdown heading syntax, handles a blank separator before bullets, excludes the generic header from retrieval/allocation, and closes objective scope when narrative text or the next section begins. Regression tests cover the exact failed input. No question/source/approval checks are relaxed.

The long comparison sentence also matches zero indexed passages under the current conjunctive lexical search, whereas `shunt and dead space` matches 47 owned, ready trusted passages. The bounded clinical control will therefore use `Compare shunt and dead space`, verify the exact planned topic before any paid call, and keep I.A.2 explicit. This fixes the demonstrated header-routing defect; broad natural-language retrieval remains a separate limitation.

Validation for the header correction: 1,082 Python tests ran (four skipped), 207 Node checks passed, repository validation passed. A fresh read-only lecture-plan verification and at most one new respiratory candidate are pending deployment. Previous failed drafts remain unchanged.

## Live objective-heading control — correct routing, quality still held

Application `e820adb81b9ae1bcf96853d592e5045f62bd35d7` passed staging CI [44291217814](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44291217814). Build `1ea57ec0-7fc6-4083-ba42-0a74dcabfd1d` succeeded and image `2f0d26afa0a4c3772d9e1324bb07dc89d17f519c722dc895d9fa5b5ee9583998` settled before the next request.

Run [44291780922](https://github.com/elyktoast/SRNA-STUDY-TOOL/actions/runs/44291780922) first verified the exact read-only topic `Compare shunt and dead space` and I.A.2, with zero paid calls. The acceptance runner now refuses any generic-heading/topic substitution before generation, with a dedicated offline negative control. It then made exactly one fresh paid request, `b2aa3478-b24e-4aca-bdfd-1ab24921cba1`.

Draft `5b7dfe6e-bcfd-4d7c-96a1-f5f30d68daba` completed and saved as `needs_revision`, with one rewrite used and **6/10** automated checks passing. Its actual topic is the requested respiratory comparison, not simulation pedagogy. The item and all held judgments remain unchanged after this result.

Exact blockers:

- R-12.2: options-only key identification above chance across five shuffled trials.
- R-5.3: replacing the perfused/unventilated mainstem-intubation region with a ventilated/unperfused embolic region was planned to yield B, but the independent changed-stem solver selected A. The question asks about a regional gas-exchange effect while options describe systemic oxygen/CO2 consequences, including a preserved-oxygenation assertion. Do not force the solver to select B or weaken the changed-case gate.
- R-2.4: the D explanation's absent-exchange claim was held because the cited classification distinguished silent units from dead-space units. Both `rationale.distractor_breakdown.D` and `distractor_evidence.D` remain flagged. This completed judgment must not be resampled for a better grade.
- Independent option adjudication remains pending because the prerequisite quality checks failed; the missing-review completion action is not eligible.

The sole repair received these failures but did not resolve them. No second repair was attempted. This is now a demonstrated clinical/writing quality failure, not a lost runtime result or wrong-topic retrieval.

## Current status / handoff

Three fresh requests completed and saved in this work, including two requests longer than five minutes, with no observed backend crash or client disconnect. Durable budget/admission checks passed against real staging PostgreSQL. The Markdown objective-heading bug is verified fixed through an actual read-only plan and a correctly routed saved respiratory draft.

**Zero new questions passed acceptance.** The original local-anesthetic and FRC drafts still have all ten automated checks passing, with human review pending. They were not modified, approved or published. All three new drafts are held (7/10, off-topic 8/10, correctly routed respiratory 6/10).

The next quality change should address the demonstrated mismatch between regional case/lead-in and systemic response options, same-category distractor plausibility, and narrowly scoped source claims. When source evidence supplies a classification of regional states, do not expand it into unsupported whole-patient gas outcomes or infer normal oxygenation. Use a bounded new acceptance control after a concrete correction; do not reroll or regrade these completed failed drafts. Natural-language retrieval, actual personal PDF/PPTX upload in the browser, and the human clinical pilot remain open. No duplicate-index rebuild is needed; other question formats stay paused.
