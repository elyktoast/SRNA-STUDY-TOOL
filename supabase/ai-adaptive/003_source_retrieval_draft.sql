-- DRAFT ONLY: depends on 002_source_library_draft.sql.
-- No client role grants. Invoke only through a reviewed admin-authorized backend.
create table if not exists private.ai_source_course_links (
  document_id uuid not null references private.ai_source_documents(id) on delete cascade,
  course_id text not null,
  exam_id text,
  created_at timestamptz not null default now(),
  primary key(document_id,course_id)
);
alter table private.ai_source_course_links enable row level security;
revoke all on private.ai_source_course_links from public,anon,authenticated;
create index if not exists ai_source_course_links_course_idx on private.ai_source_course_links(course_id,document_id);

-- Keyword retrieval uses the existing GIN index and course metadata.
-- A passage's document must be ready before it can enter the retrieval pool.
-- The function is SECURITY INVOKER, not a public SECURITY DEFINER endpoint.
create or replace function private.ai_search_source_passages(
  p_query text,
  p_course_id text,
  p_limit integer default 12
)
returns table (
  chunk_id uuid,
  document_id uuid,
  document_title text,
  section_heading text,
  page_start integer,
  page_end integer,
  passage text,
  rank real
)
language sql
stable
security invoker
set search_path=''
as $$
  select c.id,c.document_id,d.title,s.heading,c.page_start,c.page_end,
         c.content,ts_rank_cd(c.search_vector,websearch_to_tsquery('english',p_query))::real
  from private.ai_source_chunks c
  join private.ai_source_documents d on d.id=c.document_id
  join private.ai_source_course_links l on l.document_id=d.id
  left join private.ai_source_sections s on s.id=c.section_id
  where l.course_id=p_course_id
    and d.processing_status='ready'
    and c.search_vector @@ websearch_to_tsquery('english',p_query)
  order by ts_rank_cd(c.search_vector,websearch_to_tsquery('english',p_query)) desc,c.chunk_order
  limit least(greatest(p_limit,1),30)
$$;
revoke all on function private.ai_search_source_passages(text,text,integer) from public,anon,authenticated;

-- Next iteration: separate embeddings table with explicit model name,
-- vector dimensions, normalized scores and hybrid ranking.
-- Do not expose this private function through the Data API.
