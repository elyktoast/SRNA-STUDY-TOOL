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
