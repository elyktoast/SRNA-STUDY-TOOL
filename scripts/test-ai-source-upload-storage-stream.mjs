import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceUploadStorageStream} from './ai-source-upload-storage-stream.mjs';

const path='documents/01234567-89ab-4def-8abc-0123456789ab.pdf';
function setup({body=[Uint8Array.of(1,2,3)],size=3}={}){
 const calls=[];
 const supabase={storage:{from(bucket){
  calls.push(['bucket',bucket]);
  return {
   info:async()=>({data:{size},error:null}),
   createSignedUrl:async()=>({data:{signedUrl:'https://example.test/storage/v1/object/sign/ai-textbook-sources/documents/01234567-89ab-4def-8abc-0123456789ab.pdf?token=test'},error:null})
  };
 }}};
 const fetchImpl=async(url,options)=>{
  calls.push(['fetch',url,options]);
  return {ok:true,body:new ReadableStream({start(controller){
   for(const part of body)controller.enqueue(part);
   controller.close();
  }})};
 };
 return {calls,adapter:createSourceUploadStorageStream({supabase,storageOrigin:'https://example.test/',fetchImpl})};
}
test('inspects private object metadata',async()=>{
 const {adapter}=setup();
 assert.deepEqual(await adapter.inspectObject({bucket:'ai-textbook-sources',path}),{size:3});
});
test('streams private bytes without buffering the whole PDF',async()=>{
 const {adapter,calls}=setup();
 const chunks=[];
 for await(const chunk of adapter.readObject({bucket:'ai-textbook-sources',path}))chunks.push(...chunk);
 assert.deepEqual(chunks,[1,2,3]);
 assert.equal(calls.find(x=>x[0]==='fetch')[2].redirect,'error');
});
test('rejects other buckets and unsafe paths before network calls',async()=>{
 const {adapter,calls}=setup();
 await assert.rejects(adapter.inspectObject({bucket:'other',path}),/invalid private textbook object path/);
 await assert.rejects(async()=>{for await(const _ of adapter.readObject({bucket:'ai-textbook-sources',path:'../secret.pdf'})){}},/invalid private textbook object path/);
 assert.equal(calls.length,0);
});
test('splits oversized transport chunks into bounded verification chunks',async()=>{
 const bytes=new Uint8Array(6291457);
 const {adapter}=setup({body:[bytes],size:bytes.length});
 const sizes=[];
 for await(const chunk of adapter.readObject({bucket:'ai-textbook-sources',path}))sizes.push(chunk.length);
 assert.deepEqual(sizes,[6291456,1]);
});

test('rejects signed URLs pointing to an untrusted origin',async()=>{
 const supabase={storage:{from:()=>({createSignedUrl:async()=>({data:{signedUrl:'https://other.test/storage/v1/object/sign/ai-textbook-sources/x.pdf'}})})}};
 let fetched=false;
 const adapter=createSourceUploadStorageStream({supabase,storageOrigin:'https://example.test/',fetchImpl:async()=>{fetched=true}});
 await assert.rejects(async()=>{for await(const _ of adapter.readObject({bucket:'ai-textbook-sources',path})){}},/untrusted private source URL/);
 assert.equal(fetched,false);
});

test('rejects signed URL for a different textbook in the same bucket',async()=>{
 const supabase={storage:{from:()=>({createSignedUrl:async()=>({data:{signedUrl:'https://example.test/storage/v1/object/sign/ai-textbook-sources/documents/99999999-9999-4999-8999-999999999999.pdf?token=test'}})})}};
 let fetched=false;
 const adapter=createSourceUploadStorageStream({supabase,storageOrigin:'https://example.test/',fetchImpl:async()=>{fetched=true}});
 await assert.rejects(async()=>{for await(const _ of adapter.readObject({bucket:'ai-textbook-sources',path})){}},/untrusted private source URL/);
 assert.equal(fetched,false);
});

test('accepts a relative signed URL for the exact requested PDF',async()=>{
 const relative='/storage/v1/object/sign/ai-textbook-sources/'+path+'?token=test';
 const supabase={storage:{from:()=>({createSignedUrl:async()=>({data:{signedUrl:relative}})})}};
 let fetchedUrl;
 const adapter=createSourceUploadStorageStream({
  supabase,storageOrigin:'https://example.test/',
  fetchImpl:async url=>{
   fetchedUrl=url;
   return {ok:true,body:new ReadableStream({start(controller){controller.enqueue(Uint8Array.of(37,80,68,70));controller.close()}})};
  }
 });
 const chunks=[];
 for await(const chunk of adapter.readObject({bucket:'ai-textbook-sources',path}))chunks.push(...chunk);
 assert.deepEqual(chunks,[37,80,68,70]);
 assert.equal(fetchedUrl,'https://example.test'+relative);
});
