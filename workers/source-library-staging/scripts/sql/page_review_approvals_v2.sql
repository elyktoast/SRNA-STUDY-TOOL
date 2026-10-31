-- STAGING-ONLY DRAFT. NOT APPLIED. Apply only after owner approval.
-- Protected, private approval records; no browser or Data API grants.
create table if not exists source_library_staging.page_review_approvals_v2 (
  id uuid primary key default gen_random_uuid(),
  owner_uid uuid not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  r2_key text not null,
  pdf_page integer not null check (pdf_page >= 1),
  reviewer_uid uuid not null,
  decision text not null check (decision in ('approved', 'rejected')),
  reviewed_at timestamptz not null default now(),
  revoked_at timestamptz,
  review_note text not null default '',
  unique (owner_uid, source_sha256, r2_key, pdf_page, reviewer_uid),
  check (r2_key like owner_uid::text || '/%')
);
alter table source_library_staging.page_review_approvals_v2 enable row level security;
revoke all on source_library_staging.page_review_approvals_v2 from public, anon, authenticated;
revoke create on schema source_library_staging from public, anon, authenticated;
-- No RLS policies: ordinary roles cannot read/write approvals.
-- Only a separately verified, privileged server process should manage records.
create index if not exists page_review_approvals_lookup_v2
  on source_library_staging.page_review_approvals_v2
  (owner_uid, source_sha256, r2_key, reviewer_uid, pdf_page)
  where decision = 'approved' and revoked_at is null;
