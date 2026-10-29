import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifySourceRuntimeResources} from './ai-source-runtime-preflight.mjs';
const db={query:async sql=>sql.includes('to_regclass')?{rows:[{relation:'private.snar_admins'}]}:{rows:[{table_name:'ai_source_documents'},{table_name:'ai_source_sections'},{table_name:'ai_source_chunks'},{table_name:'ai_source_processing_jobs'}]}};
test('accepts existing private schema and private bucket',async()=>{
 assert.equal(await verifySourceRuntimeResources({db,supabase:{storage:{getBucket:async()=>({data:{public:false},error:null})}}}),true);
});
test('rejects public bucket',async()=>{
 await assert.rejects(verifySourceRuntimeResources({db,supabase:{storage:{getBucket:async()=>({data:{public:true},error:null})}}}),/private source storage/);
});
test('rejects missing schema',async()=>{
 await assert.rejects(verifySourceRuntimeResources({db:{query:async()=>({rows:[]})},supabase:{storage:{getBucket:async()=>({data:{public:false}})}}}),/missing private source schema/);
});

test('rejects missing sections or job tables',async()=>{
 const incomplete={query:async()=>({rows:[{table_name:'ai_source_documents'},{table_name:'ai_source_chunks'}]})};
 await assert.rejects(verifySourceRuntimeResources({db:incomplete,supabase:{storage:{getBucket:async()=>({data:{public:false}})}}}),/missing private source schema/);
});

test('rejects absent admin authorization table',async()=>{
 const missing={query:async sql=>sql.includes('to_regclass')?{rows:[{relation:null}]}:db.query(sql)};
 await assert.rejects(verifySourceRuntimeResources({db:missing,supabase:{storage:{getBucket:async()=>({data:{public:false}})}}}),/admin authorization table/);
});
