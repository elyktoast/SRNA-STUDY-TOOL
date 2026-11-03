# Phase C: first live staging generation — operator runbook

**Status:** HOLD until staging migration and deployment verification; not evidence of a completed live AI generation. This is a staging-only procedure. Never use production credentials or a production database.

## Mandatory checkpoint readiness gate (November 2026)

**HOLD: Do not run another live Generate request yet.** The staging database migration and deployed backend must be verified first. Passing CI alone does not prove the deployed service supports resume.

1. Independently confirm staging database identity. Apply `sql/20261103_generation_checkpoints_v2.sql` **only** to staging with a privileged operator role. Never run this migration against production.
2. Run the read-only `sql/20261103_generation_checkpoint_verification_v2.sql`. Verify table exists, RLS is enabled, and anonymous/authenticated database roles have no table access. Verify the private staging backend role can read/write it.
3. Keep `AI_GENERATION_CHECKPOINTS_ENABLED` unset until stage-write, stage-load, and expiry tests pass on the deployed staging backend. The owner, textbook, request hash, and evidence hash must all match.
4. The HTTP endpoint should return a safe 429 and bounded Retry-After for provider throttling. No automatic retries. Resume requires the exact same item_id, topic, blueprint, textbook, and filters; a new item_id means a new run.
5. Confirm deployment SHA and one dry-run preflight. Only then tell the owner **READY TO TEST** and authorize one controlled live attempt.

Gemini provider routing remains a declarative plan, not a deployed inference integration. Intermediate checkpoints are not published questions and are not the admin draft bank.

## Preconditions

1. Confirm focused **Source Library staging checks** and **Study Studio acronym readability tests** pass on the same SHA. Full Quality gates are manual before merge.
2. Use the **staging-only** indexed PostgreSQL database and a staging admin source-owner UUID. Confirm the chosen textbook is indexed and the topic returns passages through the authenticated `POST /generation/preflight` route. This HTTP endpoint is **read-only** and **cannot execute generation**.
3. Use a trusted backend shell/container with the Python dependencies and repository scripts, not a browser, GitHub Actions secret dump, or the public Cloudflare upload Worker.
4. Configure `DATABASE_URL` from the staging database secret manager. Set `STAGING_ONLY=true`. The operator must separately configure `AI_PROVIDER_ENDPOINT` (HTTPS OpenAI-compatible chat completions), `AI_ALLOWED_HOSTS` (exact endpoint hostname), `AI_GENERATOR_MODEL`, and `AI_PROVIDER_API_KEY` from a secret manager. Do not print or commit values.
5. Obtain explicit owner approval for **one potentially billable model generation**. Only then set `AI_GENERATION_OPT_IN=true`. No automatic retry or batch.
6. Select a narrow clinical topic, a **verified indexed staging textbook ID**, and a matching NCE/SEE domain/section/objective. Section is a single letter, e.g. `H`, while objective is a full path, e.g. `III.H.4`. These example blueprint values are syntax examples, not a claim of alignment with any particular topic.

## Step 1 — No-cost source preflight

Run from the trusted staging backend, using real values for the placeholders:

```sh
python workers/source-library-staging/scripts/run_grounded_generation_v2.py \
  "<NARROW_TOPIC>" --owner-uid "<STAGING_OWNER_UUID>" \
  --textbook-id "<INDEXED_STAGING_TEXTBOOK_ID>" \
  --mode NCE --domain III --section H --objective III.H.4 \
  --format MC --item-id "staging-live-mc-001" --limit 4
```

Expect `dry_run: true`, `passage_count > 0`, `can_publish: false`, and `database_writes: false`. Stop if the index is empty or the selected objective is inappropriate. **This command does not call the AI provider.**

## Step 2 — One explicitly authorized live draft

After confirming owner approval and setting `AI_GENERATION_OPT_IN=true`:

```sh
python workers/source-library-staging/scripts/run_grounded_generation_v2.py \
  "<NARROW_TOPIC>" --owner-uid "<STAGING_OWNER_UUID>" \
  --textbook-id "<INDEXED_STAGING_TEXTBOOK_ID>" \
  --mode NCE --domain III --section H --objective III.H.4 \
  --format MC --item-id "staging-live-mc-001" --limit 4 \
  --execute --confirm-paid-calls
```

This makes up to three sequential model calls (concept card, draft, rationale), with **no automatic retries**. The CLI returns review metadata and screening diagnostics; it does not save the generated item or publish it. Do not assume the UI will show the question from this CLI run.

## Step 3 — Acceptance criteria

- Confirm three stages completed or capture the failure stage and a **redacted** error.
- Confirm every keyed answer and distractor has a grounded passage ID and justification, and that the question has no unsupported facts, invented citations, or misleading printed-page numbers.
- Review the stem, four options, key, explanation, and clinical accuracy against the **original textbook page image**; PDF page locations alone are not verified printed-page citations.
- Confirm screening returns the expected human-review state; `can_publish=false` and `database_writes=false` throughout.
- Record elapsed time, provider/model, estimated token/cost usage from the provider dashboard, format, evidence count, and review issues. **Never log textbook excerpts, API keys, tokens, or private source material** in CI or public PR comments.
- Stop after the first draft and inspect the outcome before attempting a second question or another format.

## Known limitations

- A passing CI run verifies deterministic tests, **not** real model quality or a live staging generation.
- `/generation/preflight` is deliberately incapable of paid execution; use the trusted backend CLI for the first test.
- The current CLI does not persist the full draft for admin UI review; reviewer must inspect results in the trusted backend. An authenticated draft-review UI/storage workflow is a separate milestone.
- A live generation has **not** been performed by creating this runbook.
