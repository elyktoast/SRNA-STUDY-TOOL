import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
const names=['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs','ai_source_course_links','ai_source_upload_intents'];
const setup=(missing=[],publicBucket=false,rlsOff=[],missingColumns=[])=>({
 db:{async query(sql){
  if(sql.includes('information_schema.tables')) return {rows:names.filter(n=>!missing.includes(n)).map(table_name=>({table_name}))};
  if(sql.includes('information_schema.columns')) return {rows:(sql.includes('ai_source_upload_intents')?['r2_multipart_id','r2_completed_at']:['printed_page','section_heading']).filter(n=>!missingColumns.includes(n)).map(column_name=>({column_name}))};
  if(sql.includes('pg_class')) return {rows:names.map(relname=>({relname,relrowsecurity:!rlsOff.includes(relname)}))};
  if(sql.includes('has_table_privilege')||sql.includes('has_schema_privilege'))return {rows:[]};
  return {rows:[{relation:'private.snar_admins'}]};
 }},
 supabase:{storage:{getBucket:async()=>({data:{public:publicBucket},error:null})}}
});
test('private resources pass startup checks',async()=>assert.equal(await verifySourceRuntimeResources(setup()),true));
test('missing course links prevent startup',async()=>assert.rejects(verifySourceRuntimeResources(setup(['ai_source_course_links'])),/missing private source schema/));
test('RLS disabled prevents startup',async()=>assert.rejects(verifySourceRuntimeResources(setup([],false,['ai_source_chunks'])),/RLS disabled/));
test('public textbook bucket prevents startup',async()=>assert.rejects(verifySourceRuntimeResources(setup([],true)),/private source storage bucket unavailable/));

test('missing printed-page metadata blocks startup',async()=>assert.rejects(verifySourceRuntimeResources(setup([],false,[],['printed_page'])),/citation metadata schema missing/));
