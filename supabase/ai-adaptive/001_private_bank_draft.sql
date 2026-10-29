-- DRAFT ONLY: review and test before applying to Supabase.
-- Existing student CAT tables and storage buckets are untouched.
create table if not exists private.ai_generated_questions (
  id uuid primary key default gen_random_uuid(),
  course_id text not null,
  exam_id text not null,
  topic text not null,
  stem text not null,
  options jsonb not null,
  answer_key jsonb not null,
  explanation text not null,
  source_evidence jsonb not null default '[]'::jsonb,
  generation_metadata jsonb not null default '{}'::jsonb,
  target_difficulty numeric,
  status text not null default 'draft' check (status in ('draft','validating','needs_review','approved','published','rejected','quarantined','archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table private.ai_generated_questions enable row level security;
revoke all on private.ai_generated_questions from public, anon, authenticated;
create index if not exists ai_generated_questions_review_idx on private.ai_generated_questions(status, created_at desc);

create table if not exists private.ai_question_validations (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references private.ai_generated_questions(id) on delete cascade,
  validator text not null,
  passed boolean not null,
  findings jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);
alter table private.ai_question_validations enable row level security;
revoke all on private.ai_question_validations from public, anon, authenticated;

create table if not exists private.ai_question_reviews (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references private.ai_generated_questions(id) on delete restrict,
  reviewer_id uuid references auth.users(id) on delete set null,
  action text not null,
  details jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
alter table private.ai_question_reviews enable row level security;
revoke all on private.ai_question_reviews from public, anon, authenticated;

create table if not exists private.ai_question_publications (
  id uuid primary key default gen_random_uuid(),
  question_id uuid not null references private.ai_generated_questions(id) on delete restrict,
  course_id text not null,
  exam_id text not null,
  published_uid text not null unique,
  published_at timestamptz not null default now(),
  retired_at timestamptz,
  unique(question_id, course_id, exam_id)
);
alter table private.ai_question_publications enable row level security;
revoke all on private.ai_question_publications from public, anon, authenticated;

-- Intentionally no public read RPC, no student grants, and no publishing RPC.
-- Before use: add evidence/version lineage, source tables, server authorization,
-- validation constraints, negative RLS tests, and a rollback strategy.
