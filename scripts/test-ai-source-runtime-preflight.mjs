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
   return {rows:[{column_name:'printed_page'},{column_name:'section_heading'}]};
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
test('rejects public Storage bucket',async()=>{
 await assert.rejects(verifySourceRuntimeResources(fixture({publicBucket:true})),/private source storage bucket/);
});
test('rejects bucket smaller than required large PDF',async()=>{
 await assert.rejects(verifySourceRuntimeResources(fixture({limit:41943040})),/330 MiB/);
});

test('rejects missing private textbook Storage insert policy',async()=>{
 const {db,supabase}=fixture();
 const original=db.query;
 db.query=async(sql,...args)=>sql.includes('pg_policies')?{rows:[{total:0}]}:original(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db,supabase}),/source upload policy unavailable/);
});

test('rejects missing Storage authorization helper',async()=>{
 const {db,supabase}=fixture();
 const original=db.query;
 db.query=async(sql,...args)=>sql.includes('to_regprocedure')?{rows:[{routine:null}]}:original(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db,supabase}),/source upload helper unavailable/);
});
test('checks authenticated role and helper expression in Storage policy',async()=>{
 const {db,supabase}=fixture();
 const original=db.query;
 let policyQuery='';
 db.query=async(sql,...args)=>{
  if(sql.includes('pg_policies'))policyQuery=sql;
  return original(sql,...args);
 };
 assert.equal(await verifySourceRuntimeResources({db,supabase}),true);
 assert.match(policyQuery,/authenticated/);
 assert.match(policyQuery,/can_insert_ai_source_object/);
});

test('rejects a Storage insert policy not scoped to authenticated role',async()=>{
 const {db,supabase}=fixture();
 const original=db.query;
 db.query=async(sql,...args)=>sql.includes('pg_policies')?{rows:[{total:0}]}:original(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db,supabase}),/source upload policy unavailable/);
});

test('rejects anonymous EXECUTE on source upload authorization helper',async()=>{
 const {db,supabase}=fixture();
 const query=db.query;
 db.query=async(sql,...args)=>sql.includes('has_function_privilege')?{rows:[{anon_execute:true,authenticated_execute:true}]}:query(sql,...args);
 await assert.rejects(verifySourceRuntimeResources({db,supabase}),/helper privileges unsafe/);
});
