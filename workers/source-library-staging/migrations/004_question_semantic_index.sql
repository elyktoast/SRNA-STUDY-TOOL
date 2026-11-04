-- Staging-only semantic duplicate candidate index. Do not apply to production.
-- Keep embeddings private; publication and approval remain separate.
create schema if not exists source_library_staging;
create table if not exists source_library_staging.question_semantic_index_v2 (
  item_id text primary key check (length(item_id) between 1 and 128),
  owner_uid uuid not null,
  embedding_model text not null check (length(embedding_model) between 1 and 128),
  embedding double precision[] not null check (
    array_ndims(embedding)=1 and array_length(embedding,1) between 2 and 4096
  ),
  stem_hash text not null check (stem_hash ~ '^[a-f0-9]{64}$'),
  updated_at timestamptz not null default now()
);
create index if not exists question_semantic_index_v2_owner_model
  on source_library_staging.question_semantic_index_v2(owner_uid,embedding_model);
alter table source_library_staging.question_semantic_index_v2 enable row level security;
revoke all on source_library_staging.question_semantic_index_v2
  from public, anon, authenticated;
-- No client grants or policies. Trusted staging backend only.
