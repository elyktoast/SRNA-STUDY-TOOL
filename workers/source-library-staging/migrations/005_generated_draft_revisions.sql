-- Staging-only, append-only review revisions. No publication pathway.
create schema if not exists source_library_staging;
create table if not exists source_library_staging.generated_draft_revisions_v2 (
  id uuid primary key default gen_random_uuid(),
  draft_id uuid not null references source_library_staging.generated_question_drafts_v2(id) on delete restrict,
  owner_uid uuid not null,
  revision_number integer not null check (revision_number > 0),
  parent_question_sha256 text not null check (parent_question_sha256 ~ '^[a-f0-9]{64}$'),
  revised_question_sha256 text not null check (revised_question_sha256 ~ '^[a-f0-9]{64}$'),
  question_json jsonb not null check (jsonb_typeof(question_json) = 'object'),
  issues_json jsonb not null check (jsonb_typeof(issues_json) = 'array'),
  reviewer_notes text not null check (length(trim(reviewer_notes)) > 0 and length(reviewer_notes) <= 5000),
  created_at timestamptz not null default now(),
  unique (draft_id, revision_number)
);
create index if not exists generated_draft_revisions_v2_owner_draft
  on source_library_staging.generated_draft_revisions_v2(owner_uid,draft_id,revision_number desc);
alter table source_library_staging.generated_draft_revisions_v2 enable row level security;
revoke all on source_library_staging.generated_draft_revisions_v2 from public, anon, authenticated;
-- No direct client grants/policies. Only the trusted authenticated staging reviewer may insert.
