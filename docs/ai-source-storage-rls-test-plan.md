# Source Library private TUS security test plan

Status: **draft; not deployed**. Test in isolated Supabase project before production.

## Prerequisites
1. Confirm global Storage object limit is at least 330 MiB (target 500 MiB). TUS chunking does not bypass object limits.
2. Deploy reviewed private source schema, upload intents, bucket, and RLS draft in dependency order.
3. Confirm authenticated upload uses the end-user JWT, not service-role credentials.
4. Confirm function `private.can_insert_ai_source_object` can be invoked from a Storage policy in the target project. Keep the private schema unexposed to the Data API.

## Authorization tests
- A user with an owned, unexpired `uploading` intent may create **only** `documents/<intent-id>.pdf` in `ai-textbook-sources`.
- A different user cannot create an object for that intent.
- An intent in `pending`, `verifying`, `completed`, `failed`, or `expired` must not authorize insertion.
- Expired intents must be denied even if status is `uploading`.
- Other buckets and paths are denied.
- Browser listing, reading, deletion, and overwriting of private textbooks are denied.
- Anonymous callers are denied.
- Attempting to upload a non-PDF MIME type is denied at bucket level.

## Transfer tests
- 8-byte PDF, 6 MiB+ PDF, interrupted 20 MiB PDF, and full 330 MiB PDF.
- Resume after browser restart with the same signed-in account.
- Cross-account resume must fail.
- Repeated upload to the same path must not overwrite a verified textbook.
- Verify TUS initiation and chunk PATCH authorization behavior with Storage's current implementation; a policy on INSERT alone may not cover every resumable lifecycle operation.
- Confirm actual object size and SHA-256 from a streamed server read; do not trust browser-provided metadata.
- Confirm finalizer transaction creates exactly one document and rejects concurrent/repeated finalization.
- Test cancellation, stalled transfers, expiration, orphan cleanup, and retry after failure.

## Release gate
Do not enable production upload UI until all security and large-file tests pass, the bucket exists, and runtime preflight confirms project limits. Do not merge without explicit user approval.
