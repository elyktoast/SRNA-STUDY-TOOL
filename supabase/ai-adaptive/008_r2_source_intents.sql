-- R2 is the destination for new textbook uploads. Existing Supabase objects, if any,
-- remain readable until an explicitly approved cleanup.
alter table private.ai_source_upload_intents
 drop constraint if exists ai_source_upload_intents_storage_bucket_check;
alter table private.ai_source_upload_intents
 add constraint ai_source_upload_intents_storage_bucket_check
 check(storage_bucket in ('ai-textbook-sources','srna-private-textbooks'));
alter table private.ai_source_upload_intents
 alter column storage_bucket set default 'srna-private-textbooks';
