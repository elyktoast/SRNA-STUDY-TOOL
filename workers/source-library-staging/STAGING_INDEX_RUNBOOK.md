# Staging textbook indexing — operator runbook

This workflow is **manual only**. Do not run against production, merge the staging branch, or enable scheduled indexing until the first import is reviewed.

## GitHub environment setup

Create the GitHub Actions environment `source-library-staging` (Settings → Environments) and restrict deployments to branch `feature/source-library-r2-staging`. Add these **environment secrets**:

- `STAGING_R2_ACCOUNT_ID`: Cloudflare account ID (not a token).
- `STAGING_R2_ACCESS_KEY_ID`: R2 API key ID, scoped to the **srna-staging-textbooks** bucket.
- `STAGING_R2_SECRET_ACCESS_KEY`: matching R2 secret.
- `STAGING_DATABASE_URL`: direct/pooler PostgreSQL connection string for the **staging Supabase project** with permission to write only the private `source_library_staging` schema where possible.

Never put secret values in GitHub files, PR comments, workflow inputs, browser storage, or logs. Keep the environment restricted to the staging branch. Confirm the database connection points to the intended project before `apply=true`.

## First dry run

From Actions, choose **Source Library staging indexing (manual)** → Run workflow, branch `feature/source-library-r2-staging`.

Inputs:
- `owner_uid`: the authenticated admin owner UUID for the uploaded textbook.
- `limit`: `1`.
- `apply`: `false`.
- `ocr`: `true`.

Review the resulting extraction metadata and confirm the R2 object and SHA-256, PDF page count, detected bookmarks, OCR failures, low-text pages, and passage count. The dry run **does not** write the extracted text to Supabase. A successful dry run alone does not verify citation quality or interpretation of diagrams.

## First controlled import

Only after inspecting the dry-run result, repeat with `apply=true`, `limit=1`, `ocr=true`. The workflow reports an error if any per-book processing fails. Check the private Supabase schema afterward: verify the textbook is `ready`, page references match the PDF, section hierarchy matches bookmarks, and sample owner-scoped full-text searches return expected passages. Flag short OCR pages, diagrams, and image-only tables for manual review.

If the workflow cannot start because the GitHub environment or secrets are missing, configure them first; do not weaken Cloudflare access controls or substitute production credentials.

## Limitations

The runner currently processes the owner's backlog in R2 key order and skips records already marked `ready` when the database is configured. It is not an upload-triggered service, has no automated retries or AI vision interpretation, and should not be treated as citation verification.
