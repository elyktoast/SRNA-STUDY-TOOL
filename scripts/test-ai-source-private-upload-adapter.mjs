import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createPrivateUploadAdapter} from './ai-source-private-upload-adapter.mjs';
test('uploads PDF without overwrite and deletes exact path',async()=>{
 const calls=[];
 const storage={upload:async(...a)=>{calls.push(a);return {error:null}},remove:async paths=>{calls.push(paths);return {error:null,data:[]}}};
 const adapter=createPrivateUploadAdapter({storage:{from:bucket=>{assert.equal(bucket,'ai-textbook-sources');return storage}}});
 await adapter.uploadPrivate('admin/book.pdf',new Uint8Array([1]));
 await adapter.removePrivate('admin/book.pdf');
 assert.equal(calls[0][2].upsert,false);
 assert.deepEqual(calls[1],['admin/book.pdf']);
});
test('propagates storage upload errors',async()=>{
 const adapter=createPrivateUploadAdapter({storage:{from:()=>({upload:async()=>({error:Error('storage unavailable')})})}});
 await assert.rejects(adapter.uploadPrivate('book.pdf',new Uint8Array([1])),/storage unavailable/);
});
