import {test} from 'node:test';
import assert from 'node:assert/strict';
import {uploadAdminSource} from './ai-source-upload-service.mjs';
const pdf=new Uint8Array([37,80,68,70,45,49,46,55,10]);
const base=()=>({actorId:'admin',authorizeAdmin:async()=>true,bytes:pdf,title:'Book',storagePath:'admin/book.pdf',uploadPrivate:async()=>{},createRecord:async()=>({id:'book'}),removePrivate:async()=>{}});
test('authorized upload returns document record',async()=>{
 assert.equal((await uploadAdminSource(base())).id,'book');
});
test('unauthorized user cannot upload',async()=>{
 const x=base();let accessed=false;x.authorizeAdmin=async()=>false;x.uploadPrivate=async()=>{accessed=true};
 await assert.rejects(uploadAdminSource(x),/access denied/);
 assert.equal(accessed,false);
});
test('failed metadata write cleans up private file',async()=>{
 const x=base();let cleaned=false;x.createRecord=async()=>{throw Error('db failed')};x.removePrivate=async()=>{cleaned=true};
 await assert.rejects(uploadAdminSource(x),/db failed/);
 assert.equal(cleaned,true);
});
test('unsafe storage paths are rejected',async()=>{
 const x=base();x.storagePath='../outside.pdf';
 await assert.rejects(uploadAdminSource(x),/storage path/);
});
