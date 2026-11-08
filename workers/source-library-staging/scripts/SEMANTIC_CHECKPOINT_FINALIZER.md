# Finalizing partial embedding checkpoints

`finalize_semantic_checkpoint_v2.py` is a staging-only helper designed to
be invoked by a future authorized batch workflow with `if: always()`.

It makes **zero** provider requests. If a checkpoint exists, it validates the
canonical inventory digest, stem hashes, model, vectors and dimensions, then
saves an immutable Fernet-encrypted snapshot to staging R2 using the previously
merged transport.

Example after a separately authorized backfill run:

```sh
python finalize_semantic_checkpoint_v2.py \
  /secure/private-stems.json /secure/progress.jsonl \
  /secure/vectors.json --snapshot run-12345
```

The helper returns `saved: false` when no checkpoint exists. Corrupt or
incompatible checkpoints fail without uploading. Existing remote snapshot IDs
cannot be overwritten.

**Integration prerequisites:** The future Actions job must restore a
previously recorded snapshot, validate it *before* making paid calls, use
a unique new snapshot ID, serialize writers, and run this finalizer even
after a provider error. Do not use this helper as an excuse to re-run the
25-request pilot; that authorization has been consumed. The current
`pilot-25` workflow remains unchanged.
