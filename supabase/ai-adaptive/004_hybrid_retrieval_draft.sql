-- DRAFT ONLY. Requires 002 and 003, plus vector extension enabled.
-- Choose and lock embedding model before ingest; 384 dimensions are provisional.
create table if not exists private.ai_source_embeddings (
  chunk_id uuid not null references private.ai_source_chunks(id) on delete cascade,
  model_id text not null,
  embedding extensions.vector(384) not null,
  embedded_at timestamptz not null default now(),
  primary key(chunk_id,model_id)
);
alter table private.ai_source_embeddings enable row level security;
revoke all on private.ai_source_embeddings from public,anon,authenticated;
create index if not exists ai_source_embeddings_model_idx on private.ai_source_embeddings(model_id);

-- Combine full-text and vector search using reciprocal rank fusion.
-- Always scope retrieval to a ready document and authorized course.
create or replace function private.ai_hybrid_source_passages(
 p_query text,
 p_query_embedding extensions.vector(384),
 p_model_id text,
 p_course_id text,
 p_limit integer default 12
)
returns table(chunk_id uuid,document_id uuid,document_title text,
 section_heading text,page_start integer,page_end integer,passage text,
 combined_score double precision)
language sql stable security invoker set search_path=''
as $$
with eligible as (
 select c.id,c.document_id,c.section_id,c.chunk_order,c.content,
        c.page_start,c.page_end,c.search_vector,d.title
 from private.ai_source_chunks c
 join private.ai_source_documents d on d.id=c.document_id
 join private.ai_source_course_links l on l.document_id=d.id
 where l.course_id=p_course_id and d.processing_status='ready'
), keyword as (
 select e.id,row_number() over(order by ts_rank_cd(e.search_vector,
   websearch_to_tsquery('english',p_query)) desc,e.id) as rnk
 from eligible e
 where e.search_vector @@ websearch_to_tsquery('english',p_query)
 order by ts_rank_cd(e.search_vector,websearch_to_tsquery('english',p_query)) desc
 limit 60
), semantic as (
 select e.id,row_number() over(order by v.embedding <=> p_query_embedding,e.id) as rnk
 from eligible e
 join private.ai_source_embeddings v on v.chunk_id=e.id and v.model_id=p_model_id
 order by v.embedding <=> p_query_embedding,e.id
 limit 60
), ranked as (
 select coalesce(k.id,s.id) id,
        (coalesce(1.0/(60+k.rnk),0.0)+coalesce(1.0/(60+s.rnk),0.0)) score
 from keyword k full outer join semantic s on s.id=k.id
)
select e.id,e.document_id,e.title,sec.heading,e.page_start,e.page_end,
       e.content,r.score::double precision
from ranked r join eligible e on e.id=r.id
left join private.ai_source_sections sec on sec.id=e.section_id
order by r.score desc,e.id
limit least(greatest(p_limit,1),30)
$$;
revoke all on function private.ai_hybrid_source_passages(text,extensions.vector(384),text,text,integer) from public,anon,authenticated;

-- No public endpoint. Backend must authenticate admin and authorize course.
-- Verify extension schema, dimension, plans, model licensing and search quality
-- before migration. No HNSW index yet; add after representative benchmarks.
