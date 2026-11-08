# Phase C checkpoint restore preflight in GitHub Actions

The `Phase C Gemini embedding pilot` workflow now offers a
`checkpoint-preflight` mode with a required `checkpoint_snapshot` ID.

This mode exports the current private canonical inventory, restores the named
Fernet-encrypted checkpoint from staging R2, then validates inventory digest,
embedding model, canonical stem hashes, vector dimensions, and checkpoint
integrity. It does **not** call Gemini, create a new checkpoint, write to a
database, or deploy production code.

Required secrets in the `source-library-staging` GitHub environment:

- `SEMANTIC_CHECKPOINT_ENCRYPTION_KEY` (stable Fernet key)
- `STAGING_R2_ACCOUNT_ID`
- `STAGING_R2_ACCESS_KEY_ID`
- `STAGING_R2_SECRET_ACCESS_KEY`

The snapshot must already exist; missing snapshots fail closed. The earlier
25-request pilot deleted its checkpoint and therefore **cannot be restored**.
Do not run `checkpoint-preflight` expecting that pilot data to exist.

The workflow continues to serialize executions with its existing concurrency
group and securely removes temporary files on exit. Future work must add
immutable save-on-failure and explicit paid-batch authorization before this can
be used for resumable generation. Do not reuse `pilot-25` for paid calls
without new authorization.
