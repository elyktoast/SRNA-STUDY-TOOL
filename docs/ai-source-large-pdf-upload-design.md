# Large textbook PDF ingestion — implementation contract

Status: **design only; resumable uploader not implemented**. Target: 500 MiB per PDF (largest known textbook: 330 MB). Do not claim readiness until the end-to-end tests pass.

## Storage prerequisite

1. Confirm Supabase project tier and global Storage object-size limit >= 500 MiB. Chunked TUS transfers do **not** bypass the global object-size limit.
2. Review and apply `supabase/ai-adaptive/004_private_pdf_bucket_draft.sql` only after confirming the global limit. Bucket is private, PDF-only, 500 MiB; no broad client Storage policies.
3. If project cannot support 500 MiB objects, choose a different private object store or eligible plan before implementing transfers.

## Resumable upload architecture

- Browser sends a small JSON request to a same-origin, authenticated admin API to initiate a transfer. Server verifies the session against Supabase Auth and `private.snar_admins`, validates title and intended size (8 bytes–500 MiB), and allocates a random object path and upload ID. **Never send service-role credentials to the browser.**
- Preferred approach: server-controlled TUS proxy or a short-lived, object-scoped upload authorization supported by the storage provider. Do not add a general `authenticated` insert policy on `storage.objects` merely to enable TUS.
- Use Supabase's documented TUS 6 MiB chunk size, retries and resume support; send progress events and allow explicit cancel. Persist only opaque transfer IDs in the browser.
- On completion, server verifies object exists in the expected private bucket, actual byte count, PDF signature, and SHA-256 checksum, then creates the document DB record. Never trust browser-supplied checksum, file size, bucket, or object path as proof.
- If verification or DB insert fails, delete the uploaded object (or queue a privileged cleanup job); expire abandoned uploads and avoid duplicate completion records.
- Keep a transfer in a non-ready state until verified and indexed; only `ready` documents participate in retrieval.

## Processing and memory

The existing `/source/upload` route buffers the entire request and currently caps it at 40 MiB; it **does not** support 330 MB textbooks. Keep it capped or disable it during migration. The existing private download reader also calls `arrayBuffer()`, and PDF.js consumes an in-memory byte array. Test memory limits for 330–500 MiB files; prefer bounded concurrency and a worker process before enabling production uploads. Do not mistake chunked network upload for chunked PDF parsing.

## Acceptance tests

- Admin can upload a 330 MB PDF, interrupt transfer, resume without duplicate records, and observe progress.
- Non-admin and anonymous callers cannot initiate, resume, complete, read, list, or delete a textbook upload.
- Oversize and non-PDF files rejected; mismatched size/checksum rejected; incomplete uploads never indexed.
- Duplicate completion and concurrent retries idempotent; orphan cleanup tested.
- Document extraction and chapter/page citations verified on real textbooks; OCR-required pages fail visibly instead of being silently skipped.
- Source API and database remain healthy during a large upload and during a failed worker process.

References: https://supabase.com/docs/guides/storage/uploads/resumable-uploads and https://supabase.com/docs/guides/storage/uploads/file-limits
