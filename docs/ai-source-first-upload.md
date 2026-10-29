# First private textbook upload: operator checklist

This is a **staging-only** test procedure for the `feat/ai-adaptive-foundation` branch. Do not merge, deploy to production, or upload licensed textbooks until the operator explicitly approves.

## 1. Prerequisites

- Confirm the private Cloudflare R2 bucket `srna-private-textbooks` exists and public access is disabled.
- Configure the bucket's CORS rule for the **exact staging website origin**: allow `PUT`, permit the headers used by the signed multipart PUT, and expose `ETag`. Avoid wildcard origins.
- Apply and verify Supabase source migrations, including `supabase/ai-adaptive/008_r2_source_intents.sql` and `009_r2_multipart_sessions.sql`. Startup checks validate the private schema, RLS, required columns and admin table.
- Provision a **server-side** runtime with `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SOURCE_DATABASE_URL`, `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, and `R2_SECRET_ACCESS_KEY`. Never expose any of these secrets to client JavaScript.
- Install project dependencies and run `npm run test:ai-source`. Do not interpret a passing mocked test suite as a live R2 test.

## 2. Connect the private API

Run `npm run start:ai-source` in the trusted server runtime. By design it listens on `127.0.0.1:8787` by default. Place a TLS-terminating, authenticated reverse proxy in front of it and forward the exact `/source/*` paths without stripping their prefix. Preserve the `Authorization` header. Do not expose the loopback service directly or proxy arbitrary paths.

The staging `source-library.html` defaults to **same-origin** requests. If the API is on a separate HTTPS origin, set `window.SRNA_SOURCE_API_URL` before the page's module script executes, and configure narrowly scoped CORS for the staging origin, `POST` and `Authorization` / `Content-Type` headers. Prefer same-origin routing so no API CORS policy is needed. R2 signed-part PUT CORS is a separate requirement.

## 3. Verify before sending a PDF

Run the authenticated smoke check from a trusted local terminal, supplying the staging URL and an ephemeral **admin user's** Supabase access token via environment variables:

```sh
SOURCE_API_URL=https://staging.example.org SOURCE_ACCESS_TOKEN='<ephemeral-admin-token>' node scripts/ai-source-smoke-check.mjs
```

Do not paste tokens into chat, screenshots, commits or logs. The checker only confirms that an authenticated JSON response is reachable; it does not verify R2 permissions or multipart behavior.

## 4. First real test

1. Sign in as an authorized administrator on the staging site and open `source-library.html`.
2. Select a small, non-sensitive PDF with `application/pdf` MIME type and upload it.
3. Confirm progress, R2 object presence in `documents/<upload-id>.pdf`, and a completed intent linked to a new `private.ai_source_documents` record.
4. Test a larger PDF (over 12 MiB) to exercise multiple parts, recovery and ETag handling.
5. Test cancel and network interruption; confirm that cancel aborts the session and transient failures can be resumed without creating duplicate documents.

**Recovery status:** The admin UI now offers an in-page **Resume upload** action for a failed transfer after an upload ID was received. It reuses the same selected PDF and the existing multipart session. Recovery does not survive a page reload, and live recovery has not yet been tested. If an intent-creation response is lost before the browser receives the ID, that attempt cannot be resumed from the UI.

**Known risk:** If R2 multipart completion succeeds but the subsequent database `markComplete` write fails, retrying completion may not recover cleanly. Reconcile the verified R2 object and database state before relying on this flow for production textbooks.

## 5. Acceptance criteria

A first-upload milestone is complete only when the Node test suite passes, the staging API responds with verified administrator identity, the PDF is stored privately in R2, its SHA-256/PDF signature/size verification succeeds, and the database document is created. PDF parsing, chunk indexing, source retrieval and AI question generation are **separate later milestones**.
