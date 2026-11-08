# Staging reviewer Python service

This isolated service renders verified original PDF pages with PyMuPDF. It
does not issue inspection receipts or accept approvals; all responses carry
`X-Review-Approval-Enabled: false`.

Build from the repository root:

```sh
docker build -f workers/source-library-staging/reviewer-service/Dockerfile -t srna-reviewer-staging .
```

Required **staging-only** runtime variables: `STAGING_ONLY=true`,
`STAGING_DATABASE_URL`, `STAGING_R2_ACCOUNT_ID`,
`STAGING_R2_ACCESS_KEY_ID`, `STAGING_R2_SECRET_ACCESS_KEY`,
`SUPABASE_URL`, `SUPABASE_ANON_KEY`,
`STAGING_RECEIPT_SIGNING_SECRET`. Never commit their values.

The container listens on **127.0.0.1:8789**. It is deliberately inaccessible
through a normal container port mapping. Deployment requires an explicitly
configured same-network authenticated TLS gateway or sidecar and a controlled
private service topology. Do not bind it to 0.0.0.0 without separately
implementing and verifying gateway authorization, origin controls, rate limits,
request-size limits, TLS, and production isolation.

Health: `GET /health`; authenticated previews:
`GET /review/manifest?path=<owner>/<filename>.pdf` and
`GET /review/page.png?path=<owner>/<filename>.pdf&page=1`.

This packaging is **not a deployed service**. A passing container build is not
live acceptance. No production R2 or Supabase resources may be used.

## Deployment gate (do not expose until all checks pass)

The Docker image is **not** a public HTTP service. Its Gunicorn listener is
loopback-only inside the container. Publishing port 8789 or setting a browser
`reviewerApiUrl` without a tested gateway is **not** a deployment.

Before enabling browser previews:

1. Choose a staging-only private network topology. Keep Gunicorn on loopback;
   place the TLS gateway in the **same network namespace** or explicitly
   redesign and test private connectivity. An ordinary separate sidecar container
   cannot reach another container's `127.0.0.1` listener.
2. Route only `GET /review/manifest`, `GET /review/page.png`, and
   `OPTIONS` preflights. Do not expose `/review/approve` or inspection-receipt
   APIs. The gateway must reject other paths/methods, cap query/header/body
   sizes, enforce per-user rate limits, and disable response caching.
3. Require TLS and independently enforce authenticated access at the gateway.
   The application must still validate the Supabase bearer token and protected
   reviewer role; CORS is **not** authentication.
4. Use only staging Supabase project `xqyasyambwdyhsjkftqu` and R2 bucket
   `srna-staging-textbooks`. Inject secrets through the deployment platform,
   never GitHub source or browser configuration. Use least-privilege credentials.
5. Confirm that `STAGING_ONLY=true` and the exact staging Supabase URL and
   direct/pooler database identity pass startup checks. Verify that a wrong
   project fails before any database connection is opened.
6. Test from the actual staging browser origin, including authorized preview,
   unauthorized request, invalid origin, bad PDF digest, invalid page, and
   oversized source. Inspect CORS and integrity headers; confirm no receipt
   or approval capability exists.
7. Only after live acceptance, set the staging browser's
   `window.MBU_SOURCE_LIBRARY_STAGING.reviewerApiUrl` to the **actual**
   protected HTTPS endpoint. Do not use the production domain.

**Rollback:** remove `reviewerApiUrl` from staging browser configuration and
disable the gateway route. Existing staging review queue functionality remains
separate; approvals are still disabled.

**Status:** This checklist documents prerequisites, not completed deployment.

## Phase C indexed-evidence preflight (not paid generation)

The private Python WSGI service now mounts `POST /generation/preflight`.
The staging reviewer gateway allows this route with the existing Supabase
identity check and the Python service independently checks protected admin role.
It accepts JSON topic, NCE/SEE mode, question format and optional textbook/page
filters. The endpoint forces `execute=false`, never calls an AI provider, and
returns only passage count and metadata (not textbook excerpts).

The staging browser uses `MBU_SOURCE_LIBRARY_STAGING.generationApiUrl`, which
must be the explicitly verified HTTPS reviewer gateway origin. This is separate
from the R2 upload API. **Do not configure this URL until a manual staging
reviewer gateway deployment and authenticated acceptance are successful.**
Test authorized preflight, unauthorized user, wrong origin, malformed JSON,
oversized POST, absent indexed evidence, and no paid-model calls. Never use a
production admin session or production database for acceptance. The Python
service is not reachable from the browser without the gateway deployment.
