import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceUploadIntentDb} from './ai-source-upload-intent-db.mjs';
const id='01234567-89ab-4def-8abc-0123456789ab';
test('creates a pending upload with parameterized values',async()=>{
 const calls=[];const db={query:async(...args)=>{calls.push(args);return {rowCount:1}}};
 await createSourceUploadIntentDb(db).createIntent({id,actorId:'actor',title:'Book',fileBytes:330000000,mimeType:'application/pdf',bucket:'srna-private-textbooks',storagePath:'documents/'+id+'.pdf',status:'pending',createdAt:new Date().toISOString()});
 assert.match(calls[0][0],/insert into private.ai_source_upload_intents/);
 assert.equal(calls[0][1][3],330000000);
 assert.equal(calls[0][1][1],'actor');
});
test('rejects nonpending or incorrect bucket intents',async()=>{
 const adapter=createSourceUploadIntentDb({query:async()=>{throw new Error('should not query')}});
 await assert.rejects(adapter.createIntent({status:'completed',bucket:'srna-private-textbooks'}),/invalid/);
 await assert.rejects(adapter.createIntent({status:'pending',bucket:'public'}),/invalid/);
});
test('looks up only owned unexpired intent',async()=>{
 let sql,params;
 const adapter=createSourceUploadIntentDb({query:async(s,p)=>{sql=s;params=p;return {rows:[]}}});
 assert.equal(await adapter.getOwnedIntent({uploadId:id,actorId:'actor'}),null);
 assert.match(sql,/actor_id=\$2 and expires_at>now\(\)/);
 assert.deepEqual(params,[id,'actor']);
});
test('rejects invalid intent lookup before SQL',async()=>{
 const adapter=createSourceUploadIntentDb({query:async()=>{throw new Error('should not query')}});
 await assert.rejects(adapter.getOwnedIntent({uploadId:'bad',actorId:'actor'}),/invalid upload ID/);
});
test('claims verification only from uploadable state, for owner, before expiry',async()=>{
 let sql,params;
 const adapter=createSourceUploadIntentDb({query:async(s,p)=>{sql=s;params=p;return {rows:[{id}]}}});
 assert.deepEqual(await adapter.claimVerification({uploadId:id,actorId:'actor'}),{id});
 assert.ok(sql.includes("status='uploading'"));
 assert.match(sql,/actor_id=\$2/);
 assert.match(sql,/expires_at>now\(\)/);
 assert.deepEqual(params,[id,'actor']);
});

test('marks only an owned verifying upload as failed',async()=>{
 let sql,params;
 const adapter=createSourceUploadIntentDb({query:async(s,p)=>{sql=s;params=p;return {rowCount:1}}});
 await adapter.failVerification({uploadId:id,actorId:'actor'});
 assert.ok(sql.includes("status='verifying'"));
 assert.ok(sql.includes("status='failed'"));
 assert.deepEqual(params,[id,'actor']);
});
test('rejects failed transition when another worker owns state',async()=>{
 const adapter=createSourceUploadIntentDb({query:async()=>({rowCount:0})});
 await assert.rejects(adapter.failVerification({uploadId:id,actorId:'actor'}),/transition unavailable/);
});
