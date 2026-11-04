-- Read-only targeted textbook coverage report. Run on STAGING only.
-- Replace the UUID with the chosen staging textbook.
with book as (
  select id,filename,page_count,status,requires_ocr_review,low_text_page_count
  from source_library_staging.textbooks
  where id='2a589498-aaa4-410f-b51a-00d3ab99eafd'::uuid
), pages as (
  select b.id,generate_series(1,b.page_count) as pdf_page from book b
), coverage as (
  select pg.pdf_page,count(p.id) as passage_count
  from pages pg
  left join source_library_staging.passages p on p.textbook_id=pg.id
    and pg.pdf_page between p.page_start and p.page_end
  group by pg.pdf_page
)
select b.filename,b.status,b.page_count,b.requires_ocr_review,b.low_text_page_count,
  count(*) filter (where c.passage_count>0) as covered_pages,
  count(*) filter (where c.passage_count=0) as uncovered_pages_count,
  coalesce(jsonb_agg(c.pdf_page order by c.pdf_page)
    filter (where c.passage_count=0),'[]'::jsonb) as uncovered_pdf_pages,
  (select count(*) from source_library_staging.source_versions v where v.textbook_id=b.id) as provenance_records,
  (select count(*) from source_library_staging.sections s where s.textbook_id=b.id) as indexed_sections
from book b cross join coverage c
group by b.id,b.filename,b.status,b.page_count,b.requires_ocr_review,b.low_text_page_count;
-- A missing passage does NOT prove OCR failed: inspect PDF page images first.
-- Do not force-reindex until incoming R2 bytes match verified source digest.
