# Admin question editor

The deployed `admin-edit-question` Supabase Edge Function provides admin-only canonical bank edits from Question Reports. It requires JWT authentication, verifies `snar_admin_status().is_admin`, validates the question payload, and writes with GitHub SHA conflict protection. Configure the server-only `GITHUB_ADMIN_TOKEN` Edge Function secret before saves can succeed. The token is never sent to browser code.
