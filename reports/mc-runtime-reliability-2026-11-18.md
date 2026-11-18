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
