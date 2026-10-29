import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
const tables=['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs','ai_source_course_links','ai_source_upload_intents'];
function clients(grants=[],schemaGrants=[]){return {db:{query:async(sql)=>({rows:sql.includes('information_schema.tables')?tables.map(table_name=>({table_name})):sql.includes('pg_class')?tables.map(relname=>({relname,relrowsecurity:true})):sql.includes('information_schema.columns')?[{column_name:'printed_page'},{column_name:'section_heading'},{column_name:'r2_multipart_id'},{column_name:'r2_completed_at'}]:sql.includes('has_table_privilege')?grants:sql.includes('has_schema_privilege')?schemaGrants:[{relation:'private.snar_admins'}]})},supabase:{storage:{getBucket:async()=>({data:{public:false,allowed_mime_types:['application/pdf'],file_size_limit:524288000},error:null})}}};}
test('source preflight accepts private schema without client grants',async()=>{await assert.doesNotReject(verifySourceRuntimeResources(clients()))});
test('source preflight rejects accidental authenticated table access',async()=>{await assert.rejects(verifySourceRuntimeResources(clients([{table_name:'ai_source_chunks',grantee:'authenticated',privilege_type:'SELECT'}])),/exposed to client roles/)});

test('rejects anonymous access to private source tables',async()=>{
 await assert.rejects(verifySourceRuntimeResources(clients([{client_role:'anon',table_name:'ai_source_documents'}])),/exposed to client roles/);
});
test('rejects authenticated access to private upload intents',async()=>{
 await assert.rejects(verifySourceRuntimeResources(clients([{client_role:'authenticated',table_name:'ai_source_upload_intents'}])),/exposed to client roles/);
});
test('source preflight rejects schema usage grants to client roles',async()=>{await assert.rejects(verifySourceRuntimeResources(clients([],[{grantee:'authenticated',privilege_type:'USAGE'}])),/schema exposed/)});
