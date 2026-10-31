# Phase B reviewer deployment package (not deployed)
Run from this directory: `npm install && npx wrangler deploy`. The Cloudflare account must support Containers. This creates a **separate staging gateway** and must not replace the existing source-library Worker.

Before deployment, set the six secrets using `npx wrangler secret put NAME` for each of:
`STAGING_DATABASE_URL`, `STAGING_R2_ACCOUNT_ID`, `STAGING_R2_ACCESS_KEY_ID`, `STAGING_R2_SECRET_ACCESS_KEY`, `SUPABASE_ANON_KEY`, and `STAGING_RECEIPT_SIGNING_SECRET`.
Do not commit values. The service checks exact staging Supabase identity at startup. Keep the browser `reviewerApiUrl` unset until live acceptance succeeds.

The gateway only allows staging-origin GET manifest/page previews, and denies approval routes. **No approval or receipt capability is enabled.** Configure and verify a staging hostname before adding the actual URL to browser settings.

Acceptance: test a verified real PDF against the staging R2 bucket; inspect PNG hash, source SHA, correct page count and chapter/page indexing, deny wrong owner, wrong origin, invalid token, altered PDF, and all approval endpoints. Revert by removing the browser URL and disabling this Worker.
