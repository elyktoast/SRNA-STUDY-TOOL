-- DRAFT: not applied to production. Admin-only access via separately reviewed backend.
-- Use one document record per edition/version; never store copyrighted PDFs in Git.
create table if not exists private.ai_source_documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  author text,
  edition text,
  source_kind text not null check(source_kind in ('textbook','lecture','notes','other')),
  storage_bucket text not null,
  storage_path text not null,
  sha256 text not null,
  mime_type text not null,
  file_bytes bigint not null check(file_bytes > 0),
  processing_status text not null default 'uploaded'
    check(processing_status in ('uploaded','extracting','indexing','ready','failed','archived')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(storage_bucket,storage_path)
);
alter table private.ai_source_documents enable row level security;
revoke all on private.ai_source_documents from public, anon, authenticated;
create index if not exists ai_source_documents_hash_idx on private.ai_source_documents(sha256);

create table if not exists private.ai_source_sections (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references private.ai_source_documents(id) on delete cascade,
  parent_section_id uuid references private.ai_source_sections(id) on delete set null,
  heading text not null,
  chapter_label text,
  section_order integer not null,
  page_start integer,
  page_end integer,
  metadata jsonb not null default '{}'::jsonb,
  check (page_start is null or page_start > 0),
  check (page_end is null or page_end >= page_start),
  unique(document_id,section_order)
);
alter table private.ai_source_sections enable row level security;
revoke all on private.ai_source_sections from public, anon, authenticated;

create table if not exists private.ai_source_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references private.ai_source_documents(id) on delete cascade,
  section_id uuid references private.ai_source_sections(id) on delete set null,
  chunk_order integer not null,
  content text not null,
  page_start integer,
  page_end integer,
  printed_page text,
  section_heading text,
  extraction_method text,
  content_hash text not null,
  search_vector tsvector generated always as (to_tsvector('english',content)) stored,
  created_at timestamptz not null default now(),
  unique(document_id,chunk_order),
  check (length(content)>0),
  check (page_start is null or page_start > 0),
  check (page_end is null or page_end >= page_start)
);
alter table private.ai_source_chunks enable row level security;
revoke all on private.ai_source_chunks from public, anon, authenticated;
create index if not exists ai_source_chunks_search_idx on private.ai_source_chunks using gin(search_vector);
create index if not exists ai_source_chunks_document_idx on private.ai_source_chunks(document_id,chunk_order);

create table if not exists private.ai_source_processing_jobs (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references private.ai_source_documents(id) on delete cascade,
  stage text not null check(stage in ('extract','ocr','sections','chunk','embed','verify')),
  status text not null default 'queued' check(status in ('queued','running','completed','failed')),
  attempts integer not null default 0 check(attempts >= 0),
  error_message text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);
alter table private.ai_source_processing_jobs enable row level security;
revoke all on private.ai_source_processing_jobs from public, anon, authenticated;
create index if not exists ai_source_jobs_queue_idx on private.ai_source_processing_jobs(status,created_at);

-- Embeddings are deliberately deferred until embedding model and dimensions are chosen.
-- Preserve original page/slide numbers, OCR confidence and extraction lineage.
-- Before deployment: private bucket, admin RPCs, grants, RLS negative tests,
-- source-to-course join table, cross-document retrieval and retention controls.
