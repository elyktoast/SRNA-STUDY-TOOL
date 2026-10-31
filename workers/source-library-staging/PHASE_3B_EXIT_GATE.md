# Master Phase 3 / v2.0 Workstream B — exit gate (staging only)

Status: **NOT COMPLETE**. This checklist is an implementation and release gate, not proof of completion.

## What is implemented
- PDF extraction, selective OCR, private passage indexing and owner-scoped search.
- Extraction quality reports and a central importer that refuses flagged pages without DB-loaded approvals.
- Applied staging-only `page_review_approvals_v2` and `reviewer_roles_v2` schema; read-only schema preflight and row-locked approval lookup. Both tables have FORCE RLS, no policies, and no anon/authenticated table grants.
- Read-only retrieval benchmark with per-case recall and PDF-page expectations; nonzero exit on failure.
- Unit tests; passing CI is **not** a live staging acceptance test.

## Database role design warning
- The staging approval table uses FORCE ROW LEVEL SECURITY with no policies. A regular table owner is blocked; a role with BYPASSRLS and SELECT can read it. The preflight now checks both properties on the current connection, but BYPASSRLS is a powerful privilege and must **not** be granted to browser roles or treated as human reviewer authentication.
- Use a dedicated, secret-bearing server-only database connection with narrowly scoped operational access. Before migration, review whether a protected SECURITY DEFINER function owned by a privileged role offers a safer alternative to broad BYPASSRLS credentials. The staging schema migration was approved and applied; a deployable trusted server connection remains unconfigured.
- Keep the reviewer session/role verification independent of the DB service connection; never infer that a service account proves the human reviewer is an admin.

## Critical integration gaps
1. **Verified identity and roles:** Staging-only Supabase /auth/v1/user identity and canonical private.snar_admins role adapters are wired into a trusted callable import service with mocked tests. **No live server route or end-to-end session validation is deployed.** The Supabase service_role cannot directly read private.snar_admins; a trusted privileged connection is still required. The lower-level importer still accepts raw identity and admin parameters and must not be exposed to clients.  `import_passages` accepts `authenticated_reviewer_uid` and `reviewer_is_admin` from its caller. These are NOT independently verified. Never expose this API to untrusted clients or treat a boolean/UID argument as proof of identity. Add a trusted server entrypoint that validates the authenticated session and admin authorization from protected server-side records. Test nonadmin, cross-owner, forged reviewer, expired session, and revoked role.
2. **Protected approval writes:** `page_review_approvals_v2.sql` was applied to staging with owner approval. A server-only approval/rejection/revocation writer exists but is not deployed. Complete a trusted image-inspection evidence path, transaction/audit semantics and session-revocation checks; then validate the writer with audited reviewer identity and PDF page-image inspection. Ordinary browser roles must not have table privileges. Test concurrent revocation/import on real Postgres.
3. **Extraction entrypoint:** `process_textbook.py --apply` currently rejects unresolved extraction warnings before calling the importer, even when DB approvals might exist. This is intentionally fail-closed. Only a trusted server import workflow may pass verified identity into the central importer; do not enable local JSON or CLI reviewer flags as a workaround.
4. **Real retrieval relevance:** Run `run_source_retrieval_benchmark_v2.py` using read-only staging credentials and manually verified fixtures (real passage IDs and expected physical PDF pages). Confirm every required case passes and inspect original page images. Do not fabricate expected IDs, log source excerpts, or equate physical PDF pages with printed textbook page numbers.
5. **Broader formats:** PDF/OCR path does not yet establish production-quality PPTX, DOCX, figures, equations or scanned-image handling. Validate representative source formats before declaring the entire upload requirement complete.
6. **Release checks:** Verify ownership isolation, storage access, idempotent reindex/versioning, source deletion and citation provenance on staging. Keep existing 7,000 questions and student progress unchanged.

## Owner approval required
- Owner approved and the page-review SQL migration was applied to staging only. Do not apply further migrations, deploy, merge, or make paid AI calls without authorization.
- Next: verify privileged server access, session validity and reviewer authority, conduct reviewed-page import and retrieval benchmark, then decide whether B acceptance criteria are met.
- Phase C may have preparatory code but **do not mark a B→C transition** until the above checks pass.

## Verified queue publication boundary (2026-10-31)

`source_review_queue_publish_v2.prepare_queue_artifacts` now produces a fingerprint-bound queue and a **proposed** PDF metadata update from a local verified extraction. It deliberately performs **no R2 writes**. A trusted server publisher is still required to (1) read and hash the actual private R2 object, (2) compare its bytes to the extracted local PDF and manifest, (3) safely persist the SHA-256 in R2 object metadata without losing the original object or racing concurrent replacement, (4) write the matching private review queue, and (5) verify the endpoint can retrieve the pair. Do not use browser-supplied queue JSON or trust an unverified local PDF to represent R2 bytes. R2 metadata cannot be assumed to support an in-place patch; plan a safe copy/rewrite strategy with source identity checks. The API intentionally returns unavailable until this publication step is completed. No approval or import is authorized by a review queue.

### Operator publication command (not yet run)

From `workers/source-library-staging/scripts`, after producing a trusted extraction directory with `manifest.json`, use:

```bash
python source_review_r2_publish_v2.py --r2-key 'OWNER_UUID/OBJECT.pdf' --extraction-dir '/path/to/extraction' --dry-run
```

Only after reviewing the dry-run, explicitly authorized staging publication can use `--apply` with the same arguments. Requires `boto3` and server-side `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`. Never expose these to a browser. The script does not extract a PDF, index passages, record page inspection, or approve any content. This is a manual operator tool, **not an automatic upload hook**. Concurrent publishers are still unsupported; serialize publications per source. The API compares the queue digest and current PDF ETag/size but is not a transactional database.

### Integrated extraction-to-queue operator workflow

`process_r2_textbook.py` now supports `--review-queue-mode dry-run` and `--review-queue-mode apply`. Both require the existing `--dry-run` indexing mode, keeping queue publication separate from database imports. The runner downloads the private PDF, extracts it, verifies the extraction manifest and R2 source fingerprint, then invokes the trusted queue publisher before its temporary extraction files are deleted.

Example verification only:

```bash
python process_r2_textbook.py --owner-uid OWNER_UUID --r2-key 'OWNER_UUID/OBJECT.pdf' --ocr --dry-run --review-queue-mode dry-run
```

After explicit operator authorization, replace the final `dry-run` with `apply` **only in `--review-queue-mode`** to write review metadata to staging R2. This does not apply a database import or approve any page. It is not an automatic upload trigger. Concurrent publication still requires serialized operator access.

### Serialized operator publication (2026-10-31 implementation)

The operator CLI and R2 extraction runner now acquire a source-scoped PostgreSQL transaction advisory lock before publishing. Configure a reachable `DATABASE_URL` using the same trusted coordination database for **all** publisher instances. The lock is held until queue and attestation writes finish; competing cooperative publishers fail closed. Repeated publication of an already attested queue is refused. No migration is required for PostgreSQL advisory locks.

**Limits:** This is cooperative coordination, not an R2 transaction or a distributed lock against external writers. Do not permit other clients to write review-queue or attestation keys. A crash after writing a queue but before attestation can leave an unpublished queue; re-run with the same trusted extraction after inspecting the state. Source PDF replacement still requires explicit invalidation/reprocessing. The new lock path requires live staging validation before any production use. The operator must explicitly authorize `--apply`; no live writes have been performed.
