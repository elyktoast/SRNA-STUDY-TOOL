-- STAGING ONLY. Immutable source identity and provenance for future safe reindexing.
-- Apply after 001_private_index_schema.sql and 002_ocr_review_metadata.sql.
create table if not exists source_library_staging.source_versions (
 id uuid primary key default gen_random_uuid(),
 textbook_id uuid not null references source_library_staging.textbooks(id) on delete restrict,
 owner_uid uuid not null,
 source_sha256 text not null check (source_sha256 ~ '^[0-9a-f]{64}$'),
 file_size_bytes bigint not null check (file_size_bytes between 5 and 314572800),
 r2_key text not null,
 recorded_at timestamptz not null default now(),
 unique (textbook_id, source_sha256),
 constraint version_owner_key check (left(r2_key,length(owner_uid::text)+1)=owner_uid::text||'/')
);
create index if not exists source_versions_owner_digest
 on source_library_staging.source_versions(owner_uid,source_sha256);
alter table source_library_staging.source_versions enable row level security;
revoke all on source_library_staging.source_versions from public, anon, authenticated;
comment on table source_library_staging.source_versions is
 'Staging source fingerprints; records are provenance, not approval or citation verification.';
-- Deliberately no unique(owner_uid,source_sha256): duplicate content can be detected
-- without conflating independently uploaded textbook records.
-- Future importer must lock the textbook row, compare the digest, and reject
-- changed sources before replacing passages or approved chapters.
