# Staging Source Library Worker

This Worker is **not deployed** by committing these files. It requires a dedicated staging Supabase project or other explicitly approved staging identity provider.

Configure `SUPABASE_URL`, `SUPABASE_ANON_KEY` and `ADMIN_USER_IDS` as Worker secrets. Never use a production service-role key. `ADMIN_USER_IDS` is a comma-separated allowlist of staging-auth user UUIDs. Keep `STAGING_ONLY=true` and bind only `srna-staging-textbooks`.

The Worker exposes `GET /health`, `GET /materials`, `POST /materials` (raw PDF body, max 20 MiB), and `GET/DELETE /materials/item?path=...`. The browser adapter must send `Authorization: Bearer <staging JWT>`, `Origin` (automatically set by browsers), and PDF content type.

Do not deploy until staging auth, Worker routes, host and isolation tests are configured. Uploads currently buffer up to 20 MiB in memory. This is an initial small-PDF test implementation, not a multipart large-textbook uploader.

## Browser configuration and isolation

The UI selects R2 storage only when `window.MBU_SOURCE_LIBRARY_STAGING.enabled === true`. The adapter also refuses requests unless the browser hostname is exactly `staging.srnastudytool.com`. The staging website must configure `window.MBU_SOURCE_LIBRARY_STAGING = { enabled: true, apiUrl: 'https://<dedicated-staging-worker-host>' }` before Study Studio loads. Do not point `apiUrl` at the production site or an unrelated Worker.

**Authentication is not yet isolated.** The adapter reads `mbu_supabase_session_v1` from staging-origin localStorage. Browser storage is isolated by hostname, but this does not guarantee the JWT belongs to a separate Supabase project. Before deployment, provision a dedicated staging Supabase Auth project, configure the staging site to authenticate against it, and set the Worker's `SUPABASE_URL` and `SUPABASE_ANON_KEY` to that same staging project. Set `ADMIN_USER_IDS` to staging user UUIDs only. Never copy production JWTs, service-role keys, or admin allowlists into staging.

The staging API host must be routed to this Worker separately from the staging website host. Keep the R2 bucket private and ensure the binding points only to `srna-staging-textbooks`. Confirm that the staging site and Worker have separate DNS/routes from production.

## Required manual verification before enabling uploads

1. Confirm the dedicated staging Supabase project and admin account exist.
2. Confirm the Worker secrets reference that staging project and the R2 binding references only the staging bucket.
3. Verify a production JWT is rejected, a staging non-admin JWT is rejected, and a staging admin JWT succeeds.
4. Verify a small PDF can be uploaded, listed, downloaded and deleted from staging, and does not appear in production.
5. Verify the production hostname cannot invoke the staging browser adapter.
6. Keep this PR unmerged until CI is green and the isolation checks above are recorded.

GitHub Actions validates source code and mocked Worker behavior only. It does **not** establish real staging identity isolation or confirm a live R2 upload.
