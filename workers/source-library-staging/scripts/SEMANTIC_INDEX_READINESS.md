# Staging semantic index readiness

This is an **authenticated, read-only** diagnostic, not an embedding backfill or an approval to generate/publish.

1. Run `npm run test:inventory` on the intended canonical bank commit.
2. Generate an inventory snapshot with `node scripts/audit-canonical-semantic-inventory.mjs --export /secure/canonical-inventory.json` (do not overwrite an existing snapshot).
3. Mount that immutable snapshot inside the staging reviewer container; set `SEMANTIC_INDEX_INVENTORY_PATH` to its readable absolute path.
4. Configure `SEMANTIC_INDEX_OWNER_UID` to the authenticated admin's UUID and `SEMANTIC_INDEX_EMBEDDING_MODEL` to the exact model used to populate `question_semantic_index_v2`. Existing `STAGING_ONLY=true` and `STAGING_DATABASE_URL` are also required.
5. With a valid staging admin bearer token and Origin `https://staging.srnastudytool.com`, GET `/generation/index-readiness`.

The response reports readiness, digest and aggregate counts; it never returns item IDs, embeddings, stems or credentials. Missing configuration, mismatched authenticated owner, invalid inventory digest, or DB errors return HTTP 503 with `ready:false`. A complete HTTP 200 response can still contain `ready:false` and missing/stale/unexpected counts.

**Important:** The current deployment does not automatically mount the inventory snapshot or backfill embeddings. Until configured, this endpoint intentionally returns unavailable. A `ready:true` response does not alone activate semantic lookup for live generation: a trusted embedding function and complete canonical inventory still need to be wired into `semantic_lookup_factory`, with candidate embedding costs approved before use. Generated questions remain unpublished and subject to clinical review.
