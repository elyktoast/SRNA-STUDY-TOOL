# Live semantic duplicate screening (staging only)

This bridge connects `/generation/one` to the existing full-index lookup. It is **disabled by default** and never makes a provider call during startup, preflight, or readiness checking.

To enable after approval, the trusted staging reviewer needs:
- `STAGING_ONLY=true` and `AI_GENERATION_OPT_IN=true`
- `AI_SEMANTIC_EMBEDDING_OPT_IN=true` (additional paid-provider consent)
- `SEMANTIC_INDEX_OWNER_UID` matching the authenticated admin
- `SEMANTIC_INDEX_EMBEDDING_MODEL=gemini-embedding-001`
- `SEMANTIC_INDEX_INVENTORY_PATH` pointing to the current canonical export
- `AI_SEMANTIC_GEMINI_API_KEY` (secret; never commit it)

First populate the staging index with embeddings from **the same model and task type** (`SEMANTIC_SIMILARITY`) using the opt-in offline importer. Importing vectors from a different model or embedding task would invalidate comparisons even if dimensions match. The importer does not generate vectors.

For an authenticated `/generation/one` request, the backend first reconciles the full owner/model index against the canonical inventory. If missing, it leaves semantic screening pending and does not call the embedding provider. When the index is complete, the candidate stem is embedded once and compared to all canonical items; similarity only flags potential duplicates for human review.

**Still required before live test:** approved provider account/key, actual canonical embedding backfill, successful staging deployment and verification. No question is auto-published. Embedding calls can incur costs; do not enable without explicit authorization.
