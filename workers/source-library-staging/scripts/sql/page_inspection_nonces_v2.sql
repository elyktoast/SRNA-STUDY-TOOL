-- Staging-only proposed one-time receipt consumption. NOT APPLIED.
-- Never store the bearer receipt itself, only a SHA-256 digest of its nonce.
create table if not exists source_library_staging.page_inspection_nonces_v2 (
  nonce_sha256 text primary key check (nonce_sha256 ~ '^[0-9a-f]{64}$'),
  owner_uid uuid not null,
  reviewer_uid uuid not null,
  source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
  r2_key text not null,
  pdf_page integer not null check (pdf_page > 0),
  expires_at timestamptz not null,
  consumed_at timestamptz,
  check (r2_key like owner_uid::text || '/%')
);
alter table source_library_staging.page_inspection_nonces_v2 enable row level security;
alter table source_library_staging.page_inspection_nonces_v2 force row level security;
revoke all on source_library_staging.page_inspection_nonces_v2 from public, anon, authenticated;
create index if not exists page_inspection_nonces_expiry_v2
  on source_library_staging.page_inspection_nonces_v2 (expires_at);
