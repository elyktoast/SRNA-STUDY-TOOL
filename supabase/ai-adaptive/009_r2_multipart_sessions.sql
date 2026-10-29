-- Keep R2 multipart session IDs server-side and bound to an owned upload intent.
alter table private.ai_source_upload_intents
 add column if not exists r2_multipart_id text,
 add column if not exists r2_completed_at timestamptz;
create unique index if not exists ai_source_r2_multipart_id_idx
 on private.ai_source_upload_intents(r2_multipart_id)
 where r2_multipart_id is not null;
