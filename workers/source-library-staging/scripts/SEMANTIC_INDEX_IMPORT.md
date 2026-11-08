# Staging offline semantic index import

This is the first write-capable index-population path. It **does not generate embeddings**, invoke paid providers, publish questions, or modify production. Obtain embeddings from a separately approved trusted provider and prepare a local bundle; do not commit embeddings, source stems, database URLs, or credentials to Git.

1. Export canonical inventory with `node scripts/audit-canonical-semantic-inventory.mjs --export /secure/inventory.json`.
For a separate, explicit private export of question stems used to compute the
embeddings, run `node scripts/audit-canonical-semantic-inventory.mjs --export-stems /secure/private-stems.json`.
This creates a new local file (mode 0600, no overwrite) containing canonical IDs,
hashes and stems; it is **not** an embedding bundle and must not be committed,
uploaded to public storage, or exposed in logs. The normal `--export` output
remains unchanged. Embedding provider usage requires separate explicit approval.

2. Prepare `/secure/vectors.json` with exactly this schema:

```json
{"schema_version":1,"inventory_digest":"<64 lowercase hex>","embedding_model":"<configured model>","entries":[{"item_id":"<canonical item id>","stem_hash":"<64 lowercase hex>","embedding":[0.1,0.2]}]}
```

The file must contain **every** canonical item once, with its current hash and a finite, nonzero embedding of identical dimensionality. No partial bundle is accepted.

3. Set `STAGING_ONLY=true` and `SEMANTIC_INDEX_EMBEDDING_MODEL` in the trusted staging environment. Validate without connecting to the database:

```sh
python import_semantic_index_v2.py /secure/inventory.json /secure/vectors.json
```

4. Only after explicit approval to write to the **staging** database, set `SEMANTIC_INDEX_IMPORT_OPT_IN=true`, `SEMANTIC_INDEX_OWNER_UID` and `STAGING_DATABASE_URL`, then run the same command with `--apply`. This uses a single transaction and performs full post-write reconciliation before commit; any error rolls back. Import does not delete rows belonging to other owners or models and will fail on such conflicts.

5. Independently verify with `check_semantic_index_readiness_v2.py` and the authenticated `/generation/index-readiness` route.

**Not yet implemented:** trusted embedding generation, approved provider integration, secure transport of the full bundle, and live semantic lookup wiring into the generation service. Until then the generator must keep duplicate screening pending rather than claiming semantic coverage.
