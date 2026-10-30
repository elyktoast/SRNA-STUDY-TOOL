# Staging Source Library Worker

This Worker is **not deployed** by committing these files. It uses a separate staging-only test user in the existing SRNA Supabase Auth project to avoid additional project charges. This shares an identity provider with production; it is not complete authentication isolation.

Configure `SUPABASE_URL`, `SUPABASE_ANON_KEY` and `ADMIN_USER_IDS` as Worker secrets. Never use a production service-role key. `ADMIN_USER_IDS` is a comma-separated allowlist of staging-auth user UUIDs. Keep `STAGING_ONLY=true` and bind only `srna-staging-textbooks`.

The Worker exposes `GET /health`, `GET /materials`, `POST /materials` (raw PDF body, max 20 MiB), and `GET/DELETE /materials/item?path=...`. The browser adapter must send `Authorization: Bearer <staging JWT>`, `Origin` (automatically set by browsers), and PDF content type.

Do not deploy until staging auth, Worker routes, host and isolation tests are configured. Uploads currently buffer up to 20 MiB in memory. This is an initial small-PDF test implementation, not a multipart large-textbook uploader.

## Browser configuration and isolation

The UI selects R2 storage only when `window.MBU_SOURCE_LIBRARY_STAGING.enabled === true`. The adapter also refuses requests unless the browser hostname is exactly `staging.srnastudytool.com`. The staging website must configure `window.MBU_SOURCE_LIBRARY_STAGING = { enabled: true, apiUrl: 'https://<dedicated-staging-worker-host>' }` before Study Studio loads. Do not point `apiUrl` at the production site or an unrelated Worker.

**No-cost shared-auth design:** The adapter reads `mbu_supabase_session_v1` from staging-origin localStorage. Create a *new staging-only test user* in the existing SRNA Supabase Auth project (not a new Supabase project or paid branch). Configure the Worker with the existing SRNA project's URL and public/publishable key, and put **only that staging test user's UUID** in `ADMIN_USER_IDS`. Never allowlist a production admin's UUID or copy a production session into staging. A valid production-user JWT must be denied because its UUID is not allowlisted. A JWT issued for the staging test user can still authenticate on the shared Supabase project; the allowlist is a Worker authorization boundary, **not** a separate JWT issuer. This means a compromised staging test-user token could potentially reach any production endpoints accessible to an ordinary authenticated user; minimize that user's privileges and verify production data access restrictions before enabling uploads. Keep the staging account out of production admin roles, enrollments, and course data.

The staging API host must be routed to this Worker separately from the staging website host. Keep the R2 bucket private and ensure the binding points only to `srna-staging-textbooks`. Confirm that the staging site and Worker have separate DNS/routes from production.

## Required manual verification before enabling uploads

1. Confirm a separate, minimally privileged staging-only test user exists in the existing SRNA Supabase Auth project and is not a production admin.
2. Confirm Worker authentication points to the existing SRNA project, `ADMIN_USER_IDS` contains only the staging test UUID, and the R2 binding references only the staging bucket.
3. Verify a real production-user JWT is rejected by the staging Worker, a different ordinary-user JWT is rejected, and the allowlisted staging test-user JWT succeeds. Confirm that the staging test user has no production administrative access.
4. Verify a small PDF can be uploaded, listed, downloaded and deleted from staging, and does not appear in production.
5. Verify the production hostname cannot invoke the staging browser adapter.
6. Keep this PR unmerged until CI is green and the isolation checks above are recorded.

GitHub Actions validates source code and mocked Worker behavior only. It does **not** establish a separate identity provider or confirm a live R2 upload.
