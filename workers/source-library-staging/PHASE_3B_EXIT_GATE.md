# Master Phase 3 / v2.0 Workstream B — exit gate (staging only)

Status: **NOT COMPLETE**. This checklist is an implementation and release gate, not proof of completion.

## What is implemented
- PDF extraction, selective OCR, private passage indexing and owner-scoped search.
- Extraction quality reports and a central importer that refuses flagged pages without DB-loaded approvals.
- Draft private `page_review_approvals_v2` schema, read-only schema preflight, row-locked approval lookup.
- Read-only retrieval benchmark with per-case recall and PDF-page expectations; nonzero exit on failure.
- Unit tests; passing CI is **not** a live staging acceptance test.

## Database role design warning
- The draft approval table uses FORCE ROW LEVEL SECURITY with no policies. A regular table owner is blocked; a role with BYPASSRLS and SELECT can read it. The preflight now checks both properties on the current connection, but BYPASSRLS is a powerful privilege and must **not** be granted to browser roles or treated as human reviewer authentication.
- Use a dedicated, secret-bearing server-only database connection with narrowly scoped operational access. Before migration, review whether a protected SECURITY DEFINER function owned by a privileged role offers a safer alternative to broad BYPASSRLS credentials. Neither option is implemented or approved yet.
- Keep the reviewer session/role verification independent of the DB service connection; never infer that a service account proves the human reviewer is an admin.

## Critical integration gaps
1. **Verified identity and roles:** `import_passages` accepts `authenticated_reviewer_uid` and `reviewer_is_admin` from its caller. These are NOT independently verified. Never expose this API to untrusted clients or treat a boolean/UID argument as proof of identity. Add a trusted server entrypoint that validates the authenticated session and admin authorization from protected server-side records. Test nonadmin, cross-owner, forged reviewer, expired session, and revoked role.
2. **Protected approval writes:** `page_review_approvals_v2.sql` is a DRAFT, not applied. Implement a privileged approval/rejection/revocation writer with audited reviewer identity and PDF page-image inspection. Ordinary browser roles must not have table privileges. Test concurrent revocation/import on real Postgres.
3. **Extraction entrypoint:** `process_textbook.py --apply` currently rejects unresolved extraction warnings before calling the importer, even when DB approvals might exist. This is intentionally fail-closed. Only a trusted server import workflow may pass verified identity into the central importer; do not enable local JSON or CLI reviewer flags as a workaround.
4. **Real retrieval relevance:** Run `run_source_retrieval_benchmark_v2.py` using read-only staging credentials and manually verified fixtures (real passage IDs and expected physical PDF pages). Confirm every required case passes and inspect original page images. Do not fabricate expected IDs, log source excerpts, or equate physical PDF pages with printed textbook page numbers.
5. **Broader formats:** PDF/OCR path does not yet establish production-quality PPTX, DOCX, figures, equations or scanned-image handling. Validate representative source formats before declaring the entire upload requirement complete.
6. **Release checks:** Verify ownership isolation, storage access, idempotent reindex/versioning, source deletion and citation provenance on staging. Keep existing 7,000 questions and student progress unchanged.

## Owner approval required
- Do not apply SQL migrations, deploy, merge, or make paid AI calls without authorization.
- Once authorized: apply migration **to staging only**, run schema preflight, verify server auth, conduct reviewed-page import and retrieval benchmark, then decide whether B acceptance criteria are met.
- Phase C may have preparatory code but **do not mark a B→C transition** until the above checks pass.
