# Encrypted staging R2 checkpoint transport

The 25-request GitHub Actions pilot validated the provider, but intentionally
deleted its temporary checkpoint. Those 25 embeddings cannot be resumed from
the previous run.

`semantic_checkpoint_r2_v2.py` prepares a **separate, opt-in** persistence
mechanism for future runs. It never calls Gemini, imports to a database,
publishes drafts, or deploys. The R2 object is encrypted with Fernet before
upload and decrypted only into an exclusive-create local file.

Dependencies: `python -m pip install 'cryptography>=43,<47' 'boto3>=1.35,<2'`

Required environment variables:

- `STAGING_ONLY=true`
- `SEMANTIC_CHECKPOINT_R2_OPT_IN=true`
- `SEMANTIC_CHECKPOINT_ENCRYPTION_KEY`: stable Fernet key (keep in GitHub
  environment secrets; never print or rotate without recovery plan)
- `STAGING_R2_ACCOUNT_ID`, `STAGING_R2_ACCESS_KEY_ID`,
  `STAGING_R2_SECRET_ACCESS_KEY`: staging R2 credentials only

Operations:

```sh
python semantic_checkpoint_r2_v2.py restore /secure/progress.jsonl
python backfill_semantic_embeddings_v2.py /secure/private-stems.json \
  /secure/progress.jsonl /secure/vectors.json --preflight
# Run a new paid backfill batch only with separate authorization.
python semantic_checkpoint_r2_v2.py save /secure/progress.jsonl
```

The encrypted object lives in `srna-staging-textbooks` under the
`private-semantic-checkpoints/` prefix. It is not exposed as a public
download or GitHub artifact. An incorrect key or invalid ciphertext fails
closed; a local checkpoint is never overwritten during restore.

**Important:** This module is not yet wired to the Actions pilot. Future
integration must guarantee checkpoint saving after partial API failures,
validate restored inventory/model before requests, and prevent concurrent
writers. Do not run another paid pilot just to test storage.

## Explicit versioned snapshots

To preserve successive batches, pass a unique snapshot identifier for each
save, then restore the **exact prior snapshot** before running the next batch:

```sh
python semantic_checkpoint_r2_v2.py restore /secure/progress.jsonl --snapshot run-100
# Validate the restored checkpoint against the canonical inventory before use.
# Run a separately authorized provider batch, if any.
python semantic_checkpoint_r2_v2.py save /secure/progress.jsonl --snapshot run-101
```

Snapshot IDs allow ASCII letters, numbers, underscores and hyphens, up to 80
characters. There is no automatic 'latest' pointer, no automatic API calls,
and no concurrent-writer coordination yet. Use a single workflow concurrency
group and a durable, externally recorded snapshot ID when integrating Actions.
The existing legacy key remains readable for backward compatibility.
