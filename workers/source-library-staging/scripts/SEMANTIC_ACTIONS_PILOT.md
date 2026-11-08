# Run the authorized Gemini embedding pilot in GitHub Actions

Workflow: **Phase C Gemini embedding pilot** (`.github/workflows/phase-c-gemini-embedding-pilot.yml`).

This workflow is **manual only**, runs only on `main`, and uses the
`source-library-staging` GitHub Actions environment. It never deploys,
writes to a database, uploads question stems, or publishes drafts.

Before selecting `pilot-25`, create an environment secret named
`AI_SEMANTIC_GEMINI_API_KEY` under **Settings → Environments →
source-library-staging → Environment secrets**. Do not paste the key
into workflow inputs, repository files, issues, or chat. If the secret is
missing, the pilot fails before making any provider calls.

1. Go to **Actions → Phase C Gemini embedding pilot → Run workflow**.
2. Select branch `main`.
3. Choose `preflight` for an entirely offline, credential-free validation.
4. When preflight passes, run again with `pilot-25`. This is an
   explicit choice allowing **at most 25 requests** in that invocation.
5. Check the `Verify checkpoint count and integrity` step. A successful
   pilot verifies exactly 25 embeddings, with no database import.

Each run exports the private canonical stems to ephemeral runner storage.
The workflow removes the private source and embedding checkpoint at the
end and does not publish artifacts. This is a **disposable pilot**, not a
persistent/resumable 9,000-item backfill. The provider may charge or
consume quota for requests that fail, and an unsuccessful run should
not be automatically rerun without checking request counts.

Do not enable automatic retries or run the pilot multiple times without
fresh authorization. A full backfill, persistent checkpoint storage,
database import, and production changes remain separate decisions.
