import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createResumableSourceIntent,MAX_TEXTBOOK_BYTES,TUS_CHUNK_BYTES} from './ai-source-resumable-intent.mjs';

const uuid='01234567-89ab-4def-8abc-0123456789ab';
const base={actorId:'admin-1',authorizeAdmin:async()=>true,
 title:'  Nurse Anesthesia  ',fileBytes:330_000_000,mimeType:'application/pdf',
 now:()=>new Date('2026-10-29T12:00:00Z'),newId:()=>uuid};
test('creates 330 MB admin intent without exposing a storage credential',async()=>{
 let saved;
 const result=await createResumableSourceIntent({...base,createIntent:async v=>{saved=v}});
 assert.equal(result.fileBytes,330_000_000);
 assert.equal(result.chunkBytes,6*1024*1024);
 assert.equal(result.title,'Nurse Anesthesia');
 assert.equal(saved.storagePath,'documents/'+uuid+'.pdf');
 assert.equal(saved.status,'pending');
 assert.equal(result.uploadId,uuid);
 assert.equal('actorId' in result,false);
 assert.equal('storagePath' in result,false);
});
test('accepts maximum 500 MiB textbook',async()=>{
 const result=await createResumableSourceIntent({...base,fileBytes:MAX_TEXTBOOK_BYTES,createIntent:async()=>{}});
 assert.equal(result.fileBytes,MAX_TEXTBOOK_BYTES);
 assert.equal(TUS_CHUNK_BYTES,6291456);
});
test('rejects oversized textbook before persistence',async()=>{
 let called=false;
 await assert.rejects(createResumableSourceIntent({...base,fileBytes:MAX_TEXTBOOK_BYTES+1,createIntent:async()=>{called=true}}),/file size/);
 assert.equal(called,false);
});
test('rejects non-admin before persistence',async()=>{
 let called=false;
 await assert.rejects(createResumableSourceIntent({...base,authorizeAdmin:async()=>false,createIntent:async()=>{called=true}}),/access denied/);
 assert.equal(called,false);
});
test('rejects non-PDF before persistence',async()=>{
 await assert.rejects(createResumableSourceIntent({...base,mimeType:'image/png',createIntent:async()=>{}}),/PDF required/);
});
test('rejects invalid title and file size',async()=>{
 for(const options of [{title:' '},{title:'x'.repeat(251)},{fileBytes:0},{fileBytes:NaN}]){
  await assert.rejects(createResumableSourceIntent({...base,...options,createIntent:async()=>{}}),/invalid/);
 }
});
test('persistence failure propagates without returning a usable upload ID',async()=>{
 await assert.rejects(createResumableSourceIntent({...base,createIntent:async()=>{throw new Error('database unavailable')}}),/database unavailable/);
});
