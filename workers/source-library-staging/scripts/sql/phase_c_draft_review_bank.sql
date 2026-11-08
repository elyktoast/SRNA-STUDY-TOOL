-- Phase C staging-only private review bank. Apply only after operator review.
-- This schema is deliberately NOT exposed via Supabase public Data API.
create schema if not exists source_library_staging;

create table if not exists source_library_staging.generated_question_drafts_v2 (
  id uuid primary key default gen_random_uuid(),
  owner_uid uuid not null,
  textbook_id uuid not null references source_library_staging.textbooks(id),
  topic text not null check (length(btrim(topic)) between 1 and 500),
  exam_mode text not null check (exam_mode in ('NCE','SEE')),
  question_format text not null check (question_format in ('MC','MS','SA','DD','HS')),
  blueprint_domain text not null,
  blueprint_section text not null,
  blueprint_objective text not null,
  provider text not null,
  model text not null,
  question_json jsonb not null check (jsonb_typeof(question_json)='object'),
  screening_json jsonb not null check (jsonb_typeof(screening_json)='object'),
  evidence_json jsonb not null check (jsonb_typeof(evidence_json)='array'),
  status text not null default 'pending_review'
    check (status in ('pending_review','needs_revision','approved_for_bank','rejected')),
  reviewer_notes text,
  reviewed_by uuid,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint draft_approval_requires_reviewer check (
    status <> 'approved_for_bank' or (reviewed_by is not null and reviewed_at is not null)
  )
);
create index if not exists generated_question_drafts_v2_owner_status_idx
  on source_library_staging.generated_question_drafts_v2(owner_uid,status,created_at desc);
create index if not exists generated_question_drafts_v2_textbook_idx
  on source_library_staging.generated_question_drafts_v2(textbook_id,created_at desc);
alter table source_library_staging.generated_question_drafts_v2 enable row level security;
revoke all on source_library_staging.generated_question_drafts_v2 from public, anon, authenticated;
-- No browser-facing policies or grants. A future authenticated staging-only backend
-- must verify the owner, source textbook ownership, reviewer identity and transitions.
-- Storing 'approved_for_bank' here does NOT publish to any canonical question bank.
