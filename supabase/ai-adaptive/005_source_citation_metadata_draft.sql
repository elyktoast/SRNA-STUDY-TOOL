-- DRAFT ONLY: apply after review alongside private source-library migrations.
-- Preserve original textbook pagination and section provenance during ingestion.
alter table private.ai_source_chunks
  add column if not exists printed_page text,
  add column if not exists section_heading text;

-- Keep all source content private; no additional grants or public policies.
