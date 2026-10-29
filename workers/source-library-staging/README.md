# Staging Source Library Worker

This Worker is **not deployed** by committing these files. It requires a dedicated staging Supabase project or other explicitly approved staging identity provider.

Configure `SUPABASE_URL`, `SUPABASE_ANON_KEY` and `ADMIN_USER_IDS` as Worker secrets. Never use a production service-role key. `ADMIN_USER_IDS` is a comma-separated allowlist of staging-auth user UUIDs. Keep `STAGING_ONLY=true` and bind only `srna-staging-textbooks`.

The Worker exposes `GET /health`, `GET /materials`, `POST /materials` (raw PDF body, max 20 MiB), and `GET/DELETE /materials/item?path=...`. The browser adapter must send `Authorization: Bearer <staging JWT>`, `Origin` (automatically set by browsers), and PDF content type.

Do not deploy until staging auth, Worker routes, host and isolation tests are configured. Uploads currently buffer up to 20 MiB in memory. This is an initial small-PDF test implementation, not a multipart large-textbook uploader.
