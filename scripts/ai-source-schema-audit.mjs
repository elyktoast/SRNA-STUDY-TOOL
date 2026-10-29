import {readFile} from 'node:fs/promises';
import {test} from 'node:test';
import assert from 'node:assert/strict';
const sql=await readFile(new URL('../supabase/ai-adaptive/002_source_library_draft.sql',import.meta.url),'utf8');
test('all source tables have RLS enabled and client privileges revoked',()=>{
 for(const table of ['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs']){
  assert.match(sql,new RegExp('create table if not exists private\\.'+table+'\\s*\\(','i'));
  assert.match(sql,new RegExp('alter table private\\.'+table+' enable row level security','i'));
  assert.match(sql,new RegExp('revoke all on private\\.'+table+' from public, anon, authenticated','i'));
 }
});
test('document and chunk columns match backend insert contracts',()=>{
 for(const name of ['title','source_kind','storage_bucket','storage_path','sha256','mime_type','file_bytes','processing_status'])
  assert.match(sql,new RegExp('\\b'+name+'\\s+(text|bigint)','i'));
 for(const name of ['document_id','chunk_order','content','page_start','page_end','content_hash','extraction_method'])
  assert.match(sql,new RegExp('\\b'+name+'\\s+(uuid|integer|text)','i'));
});
