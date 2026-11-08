# Resumable semantic embedding backfill — staging only

This script prepares the complete embedding bundle required by the offline staging importer. It makes **paid or quota-consuming Gemini requests only after explicit opt-in**; do not run it until provider usage is approved.

1. From the repository root, privately export the canonical source:
   `node scripts/audit-canonical-semantic-inventory.mjs --export-stems /secure/private-stems.json`
2. On the trusted staging operator machine, configure `STAGING_ONLY=true`,
   `AI_SEMANTIC_EMBEDDING_OPT_IN=true`,
   `SEMANTIC_INDEX_EMBEDDING_MODEL=gemini-embedding-001`, and
   `AI_SEMANTIC_GEMINI_API_KEY` in secret environment storage.
3. Run from `workers/source-library-staging/scripts`:
   `python backfill_semantic_embeddings_v2.py /secure/private-stems.json /secure/progress.jsonl /secure/vectors.json --max-new 25`
4. Repeat the command to resume, using a suitable call budget. Each successful
   embedding is appended and synced to disk; provider errors stop the batch and
   completed vectors remain available for retry. The final bundle is written
   **only after every canonical question has a vector**.
5. Export the standard inventory using `--export /secure/inventory.json`,
   then run the existing dry-run importer and separately approve `--apply`.

The checkpoint and final bundle contain proprietary question metadata and
embeddings; keep them outside Git and public storage. The script does not
modify staging or production databases and does not publish questions.
It does not silently retry failed provider calls or make calls when imported.
Each invocation defaults to a maximum of 25 *new* embedding calls.

**Important:** Gemini embeddings are requested with `SEMANTIC_SIMILARITY`.
The importer and live query must use the same model/task type. Full bank
coverage and a successful reconciliation are required before duplicate
screening can be considered complete.
