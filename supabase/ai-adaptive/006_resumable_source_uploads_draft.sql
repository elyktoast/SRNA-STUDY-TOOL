-- DRAFT ONLY: apply after 002_source_library_draft.sql and security review.
-- Server-only upload intents; no anon/authenticated grants or policies.
create table if not exists private.ai_source_upload_intents (
 id uuid primary key,
 actor_id uuid not null references auth.users(id) on delete cascade,
 title text not null check(length(btrim(title)) between 1 and 250),
 file_bytes bigint not null check(file_bytes between 8 and 524288000),
 mime_type text not null default 'application/pdf' check(mime_type='application/pdf'),
 storage_bucket text not null default 'ai-textbook-sources' check(storage_bucket='ai-textbook-sources'),
 storage_path text not null unique,
 status text not null default 'pending'
  check(status in ('pending','uploading','verifying','completed','failed','expired')),
 document_id uuid unique references private.ai_source_documents(id) on delete set null,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 expires_at timestamptz not null default (now()+interval '24 hours'),
 check(expires_at>created_at)
);
alter table private.ai_source_upload_intents enable row level security;
revoke all on private.ai_source_upload_intents from public,anon,authenticated;
create index if not exists ai_source_upload_intents_expiry_idx
 on private.ai_source_upload_intents(status,expires_at);
-- Future worker must use conditional status transitions, verify object size and
-- server-computed SHA-256, and atomically link the completed document.
-- Do not mark an intent completed merely because TUS reported success.
