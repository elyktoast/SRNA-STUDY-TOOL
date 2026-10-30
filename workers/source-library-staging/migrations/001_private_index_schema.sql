-- STAGING SOURCE LIBRARY: additive, private schema; do not apply to production.
create schema if not exists source_library_staging;
create table if not exists source_library_staging.textbooks (
 id uuid primary key default gen_random_uuid(),
 owner_uid uuid not null,
 r2_key text not null unique,
 filename text not null,
 file_size_bytes bigint not null check(file_size_bytes > 0 and file_size_bytes <= 314572800),
 status text not null default 'uploaded' check(status in ('uploaded','queued','extracting','indexing','ready','failed')),
 error_message text,
 page_count integer check(page_count >= 0),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 indexed_at timestamptz,
 constraint textbook_owner_key check(left(r2_key,length(owner_uid::text)+1)=owner_uid::text||'/')
);
create table if not exists source_library_staging.sections (
 id uuid primary key default gen_random_uuid(),
 textbook_id uuid not null references source_library_staging.textbooks(id) on delete cascade,
 parent_section_id uuid references source_library_staging.sections(id) on delete set null,
 heading text not null,
 section_order integer not null check(section_order >= 0),
 start_page integer check(start_page > 0),
 end_page integer check(end_page >= start_page),
 created_at timestamptz not null default now(),
 unique(textbook_id,section_order)
);
create table if not exists source_library_staging.passages (
 id uuid primary key default gen_random_uuid(),
 textbook_id uuid not null references source_library_staging.textbooks(id) on delete cascade,
 section_id uuid references source_library_staging.sections(id) on delete set null,
 chunk_index integer not null check(chunk_index >= 0),
 page_start integer not null check(page_start > 0),
 page_end integer not null check(page_end >= page_start),
 content text not null check(length(content)>0),
 content_search tsvector generated always as (to_tsvector('english',content)) stored,
 created_at timestamptz not null default now(),
 unique(textbook_id,chunk_index)
);
create index if not exists source_library_staging_passages_fts on source_library_staging.passages using gin(content_search);
create index if not exists source_library_staging_sections_textbook on source_library_staging.sections(textbook_id);
create index if not exists source_library_staging_passages_textbook_page on source_library_staging.passages(textbook_id,page_start);
create index if not exists source_library_staging_textbooks_owner on source_library_staging.textbooks(owner_uid);
alter table source_library_staging.textbooks enable row level security;
alter table source_library_staging.sections enable row level security;
alter table source_library_staging.passages enable row level security;
revoke all on schema source_library_staging from public, anon, authenticated;
revoke all on all tables in schema source_library_staging from public, anon, authenticated;
-- No client-facing policies or grants. Only trusted server-side service roles can ingest/search.
