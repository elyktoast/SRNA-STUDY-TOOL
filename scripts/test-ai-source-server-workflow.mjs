import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceServerWorkflow} from './ai-source-server-workflow.mjs';
test('server workflow rejects unauthorized upload and processing',async()=>{
 let touched=false;
 const db={query:async()=>{touched=true;return {rows:[]}},connect:async()=>{touched=true}};
 const supabase={storage:{from:()=>({upload:async()=>{touched=true},download:async()=>{touched=true},remove:async()=>{touched=true}})}};
 const workflow=createSourceServerWorkflow({db,supabase,authorizeAdmin:async()=>false,getDocument:()=>{}});
 await assert.rejects(workflow.upload({actorId:'student'}),/access denied/);
 await assert.rejects(workflow.process({actorId:'student',documentId:'book-1'}),/access denied/);
 assert.equal(touched,false);
});
