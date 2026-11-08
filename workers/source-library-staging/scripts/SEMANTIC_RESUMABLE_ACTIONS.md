# Manually authorized resumable Gemini batches

The `Phase C Gemini embedding pilot` workflow now supports `resumable-25`.
This mode is **manual only**, runs only on `main`, is staging-only, and
makes at most **25 new Gemini embedding requests per explicit dispatch**.
Do not dispatch without fresh authorization for those paid requests.

Provide a unique `save_snapshot` identifier for every run, such as
`batch-20261108-001`. On the first run, leave `checkpoint_snapshot`
blank. On subsequent runs, set `checkpoint_snapshot` to the exact
successful saved snapshot from the previous run, and choose a new
`save_snapshot`. Snapshot names are never automatically guessed.

Before provider requests, the workflow validates required staging secrets,
refuses an existing output snapshot, restores any requested previous
snapshot, and validates its canonical inventory/model/vector integrity.
The job's existing concurrency group serializes dispatches.

After the provider step, a separate `if: always()` finalizer validates
partial progress and saves it encrypted to staging R2. Even when the provider
fails, the finalizer can save successfully appended progress; the original
provider failure still marks the run failed. A missing or corrupt checkpoint
is not uploaded. Runner temporary data is deleted on all exits.

The `source-library-staging` GitHub environment must contain:
`AI_SEMANTIC_GEMINI_API_KEY`,
`SEMANTIC_CHECKPOINT_ENCRYPTION_KEY`,
`STAGING_R2_ACCOUNT_ID`,
`STAGING_R2_ACCESS_KEY_ID`,
and `STAGING_R2_SECRET_ACCESS_KEY`.
Never paste these values into chat or Actions logs.

No staging DB import or production deployment is performed. The original
25-request pilot's ephemeral vectors were deleted, so the first resumable
batch starts from zero. A full 9,000-vector bundle remains a separate,
explicitly gated step.
