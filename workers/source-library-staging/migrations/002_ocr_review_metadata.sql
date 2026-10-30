-- Track incomplete PDF text without falsely implying OCR/citation verification.
alter table source_library_staging.textbooks add column if not exists requires_ocr_review boolean not null default false;
alter table source_library_staging.textbooks add column if not exists low_text_page_count integer not null default 0 check (low_text_page_count >= 0);
comment on column source_library_staging.textbooks.requires_ocr_review is 'Extracted text may be incomplete; not a verified citation or OCR result';
