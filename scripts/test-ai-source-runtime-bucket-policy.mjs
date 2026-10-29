import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
const names=['ai_source_documents','ai_source_sections','ai_source_chunks','ai_source_processing_jobs','ai_source_course_links'];
function setup(bucket){return {db:{query:async sql=>({rows:sql.includes('information_schema.tables')?names.map(table_name=>({table_name})):sql.includes('pg_class')?names.map(relname=>({relname,relrowsecurity:true})):sql.includes('information_schema.columns')?[{column_name:'printed_page'},{column_name:'section_heading'}]:sql.includes('role_table_grants')?[]:sql.includes('has_schema_privilege')?[]:[{relation:'private.snar_admins'}]})},supabase:{storage:{getBucket:async()=>({data:bucket,error:null})}}};}
test('accepts PDF-only private storage',async()=>{assert.equal(await verifySourceRuntimeResources(setup({public:false,allowed_mime_types:['application/pdf'],file_size_limit:104857600})),true)});
test('rejects public storage',async()=>{await assert.rejects(verifySourceRuntimeResources(setup({public:true,allowed_mime_types:['application/pdf'],file_size_limit:104857600})),/private source storage/)});
test('rejects unrestricted MIME types',async()=>{await assert.rejects(verifySourceRuntimeResources(setup({public:false,allowed_mime_types:null,file_size_limit:104857600})),/PDF only/)});
test('rejects oversized bucket limit',async()=>{await assert.rejects(verifySourceRuntimeResources(setup({public:false,allowed_mime_types:['application/pdf'],file_size_limit:104857601})),/size limit invalid/)});
