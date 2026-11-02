# Staging textbook indexing — operator runbook

This workflow is **manual only**. The attempted scheduled trigger was removed because GitHub schedules run from the default branch, not this unmerged feature branch. Do not run against production, merge the staging branch, or enable scheduled indexing until the first import is reviewed.

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

## Fingerprint migration prerequisite

Before running an import with `apply=true`, apply `migrations/003_source_versions.sql` to the confirmed staging database after migrations 001 and 002. Check that the private `source_library_staging.source_versions` table exists. Existing indexed records with no source fingerprint cannot be safely reindexed automatically; review their original PDF provenance first. Do not apply the migration to a production database or bypass the guard.

## Background indexing status

Automatic upload-triggered indexing is **not implemented**. The manual workflow is the supported staging path until a separately approved staging scheduler or queue runner exists. A scheduled workflow in an unmerged branch cannot provide background processing. Do not set an auto-index flag expecting it to work.

## Target a specific uploaded PDF

The manual indexing workflow accepts optional `r2_key`, the exact owner-scoped object path returned by the staging uploader. With `r2_key` set, the indexer processes only that PDF, not the next item in the backlog. Leave it blank to scan pending objects. Use `apply=false` first; set `apply=true` only after the staging schema migration preflight and dry-run review. Ready textbooks are skipped unless intentionally forced for reindexing. This is not an automatic upload trigger.

## PR #34 branch conflict resolution (staging branch only)

PR #34 is draft and currently conflicts with `main` because the indexing workflow was added independently to both branches. The staging branch's workflow contains the newer `r2_key` and `force_reindex` controls; the explicit staging checkout and `persist-credentials: false` protection from `main` have already been incorporated. The chapter-audit workflow is present on both branches.

Resolve by merging **`main` into `feature/source-library-r2-staging`**, retaining the feature branch's complete `.github/workflows/source-library-index-staging.yml` when Git reports an add/add conflict. Do **not** merge PR #34 into `main` as part of this operation. If any other conflict appears, stop and review it rather than automatically choosing a side.

From a fresh local clone with write access:

```bash
git fetch origin main feature/source-library-r2-staging
git switch -c source-library-conflict-fix origin/feature/source-library-r2-staging
git merge --no-commit --no-ff origin/main
# If the indexing workflow is conflicted, preserve the staged feature-branch version:
git checkout --ours -- .github/workflows/source-library-index-staging.yml
git add .github/workflows/source-library-index-staging.yml
# Review any remaining unmerged paths before proceeding:
git diff --name-only --diff-filter=U
# Only after that command prints nothing:
git diff --cached --check
git commit -m "Merge main into staging source-library branch"
git push origin HEAD:feature/source-library-r2-staging
```

If the chapter-audit workflow is also conflicted, compare both versions and stage the intended combined file before committing. Do not use `git push --force`, `git reset --hard`, or a PR merge button. Confirm the PR is still draft and unmerged after the push, then review the newly triggered staging checks.

## Live-data safety and verification

The existing staging textbook has 595 passages but no recorded `source_versions` provenance row. Do not use `force_reindex` against it or claim its citations are verified. For end-to-end testing, use a **new, separately uploaded staging-only PDF** and a controlled one-file import, then validate source digest, page references, OCR warnings, owner-scoped search, and resulting provenance before considering automated indexing.
