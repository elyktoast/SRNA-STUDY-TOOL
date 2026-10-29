import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';

const tables=['ai_source_documents','ai_source_sections','ai_source_chunks',
 'ai_source_processing_jobs','ai_source_course_links','ai_source_upload_intents'];
function fixture({missing,unprotected,exposed=false,publicBucket=false,limit=524288000}={}){
 const db={query:async(sql)=>{
  if(sql.includes('information_schema.tables'))
   return {rows:tables.filter(t=>t!==missing).map(table_name=>({table_name}))};
  if(sql.includes('pg_class'))
   return {rows:tables.map(relname=>({relname,relrowsecurity:relname!==unprotected}))};
  if(sql.includes('information_schema.columns'))
   return {rows:(sql.includes('ai_source_upload_intents')?['r2_multipart_id','r2_completed_at']:['printed_page','section_heading']).map(column_name=>({column_name}))};
  if(sql.includes('has_table_privilege'))return {rows:exposed?[{client_role:'authenticated',table_name:'ai_source_upload_intents'}]:[]};
  if(sql.includes('has_schema_privilege'))return {rows:[]};
  if(sql.includes('has_function_privilege'))return {rows:[{anon_execute:false,authenticated_execute:true}]};
  if(sql.includes('pg_policies'))return {rows:[{total:1}]};
  if(sql.includes('to_regprocedure'))return {rows:[{routine:'public.can_insert_ai_source_object(text,text)'}]};
  if(sql.includes('to_regclass'))return {rows:[{relation:'private.snar_admins'}]};
  throw new Error('unexpected preflight query');
 }};
 const supabase={storage:{getBucket:async()=>({data:{public:publicBucket,allowed_mime_types:['application/pdf'],file_size_limit:limit},error:null})}};
 return {db,supabase};
}
test('accepts complete private schema and 500 MiB PDF bucket',async()=>{
 assert.equal(await verifySourceRuntimeResources(fixture()),true);
});
test('rejects missing upload intents table',async()=>{
 await assert.rejects(verifySourceRuntimeResources(fixture({missing:'ai_source_upload_intents'})),/missing private source schema/);
});
test('rejects upload intents without RLS',async()=>{
 await assert.rejects(verifySourceRuntimeResources(fixture({unprotected:'ai_source_upload_intents'})),/RLS disabled/);
});
test('rejects client table privileges on upload intents',async()=>{
 await assert.rejects(verifySourceRuntimeResources(fixture({exposed:true})),/exposed to client roles/);
});
test('rejects missing R2 multipart session column',async()=>{
 const {db}=fixture();const query=db.query;
 db.query=async(sql,...args)=>sql.includes("table_name='ai_source_upload_intents'")?{rows:[{column_name:'r2_completed_at'}]}:query(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db}),/R2 session schema missing/);
});
test('rejects missing R2 completion timestamp column',async()=>{
 const {db}=fixture();const query=db.query;
 db.query=async(sql,...args)=>sql.includes("table_name='ai_source_upload_intents'")?{rows:[{column_name:'r2_multipart_id'}]}:query(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db}),/R2 session schema missing/);
});
test('rejects missing private admin authorization relation',async()=>{
 const {db}=fixture();const query=db.query;
 db.query=async(sql,...args)=>sql.includes('to_regclass')?{rows:[{relation:null}]}:query(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db}),/admin authorization table unavailable/);
});
test('rejects schema usage granted to authenticated clients',async()=>{
 const {db}=fixture();const query=db.query;
 db.query=async(sql,...args)=>sql.includes('has_schema_privilege')?{rows:[{client_role:'authenticated'}]}:query(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db}),/schema exposed to client roles/);
});
