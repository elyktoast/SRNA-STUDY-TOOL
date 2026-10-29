import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
const tables=['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs','ai_source_course_links'];
function clients(grants=[]){return {db:{query:async(sql)=>({rows:sql.includes('information_schema.tables')?tables.map(table_name=>({table_name})):sql.includes('pg_class')?tables.map(relname=>({relname,relrowsecurity:true})):sql.includes('information_schema.columns')?[{column_name:'printed_page'},{column_name:'section_heading'}]:sql.includes('role_table_grants')?grants:[{relation:'private.snar_admins'}]})},supabase:{storage:{getBucket:async()=>({data:{public:false,allowed_mime_types:['application/pdf'],file_size_limit:104857600},error:null})}}};}
test('source preflight accepts private schema without client grants',async()=>{await assert.doesNotReject(verifySourceRuntimeResources(clients()))});
test('source preflight rejects accidental authenticated table access',async()=>{await assert.rejects(verifySourceRuntimeResources(clients([{table_name:'ai_source_chunks',grantee:'authenticated',privilege_type:'SELECT'}])),/exposed to client roles/)});

test('rejects unrestricted source bucket types',async()=>{const env=clients();env.supabase.storage.getBucket=async()=>({data:{public:false,allowed_mime_types:null,file_size_limit:104857600}});await assert.rejects(verifySourceRuntimeResources(env),/PDF only/)});
test('rejects source bucket over 100 MB',async()=>{const env=clients();env.supabase.storage.getBucket=async()=>({data:{public:false,allowed_mime_types:['application/pdf'],file_size_limit:200000000}});await assert.rejects(verifySourceRuntimeResources(env),/size limit invalid/)});
