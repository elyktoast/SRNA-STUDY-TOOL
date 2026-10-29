import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createR2SourceStorageAdapter,R2_SOURCE_BUCKET} from './ai-source-r2-storage.mjs';
const path='documents/01234567-89ab-4def-8abc-0123456789ab.pdf';
class HeadObjectCommand{constructor(args){this.args=args}}
class GetObjectCommand{constructor(args){this.args=args}}
function fixture(bytes=Buffer.from('%PDF-1.7\\nhello')){
 const calls=[];
 const client={async send(command){
  calls.push(command);
  if(command instanceof HeadObjectCommand)return {ContentLength:bytes.length};
  if(command instanceof GetObjectCommand)return {Body:(async function*(){yield bytes})()};
  throw new Error('unexpected command');
 }};
 return {adapter:createR2SourceStorageAdapter({client,commands:{HeadObjectCommand,GetObjectCommand}}),calls};
}
test('inspects private R2 object size using HEAD',async()=>{
 const {adapter,calls}=fixture();
 assert.equal((await adapter.inspectObject({bucket:R2_SOURCE_BUCKET,path})).size,14);
 assert.deepEqual(calls[0].args,{Bucket:R2_SOURCE_BUCKET,Key:path});
});
test('streams R2 PDF bytes without creating signed public links',async()=>{
 const {adapter}=fixture();
 const chunks=[];
 for await(const chunk of adapter.readObject({bucket:R2_SOURCE_BUCKET,path}))chunks.push(chunk);
 assert.equal(Buffer.concat(chunks).toString(),'%PDF-1.7\\nhello');
});
test('rejects unknown buckets and object paths before S3 access',async()=>{
 const {adapter,calls}=fixture();
 await assert.rejects(adapter.inspectObject({bucket:'public',path}),/invalid private R2/);
 await assert.rejects(async()=>{for await(const _ of adapter.readObject({bucket:R2_SOURCE_BUCKET,path:'other.pdf'})){}},/invalid private R2/);
 assert.equal(calls.length,0);
});
test('rejects missing private object streams',async()=>{
 const client={send:async()=>({Body:null})};
 const adapter=createR2SourceStorageAdapter({client,commands:{HeadObjectCommand,GetObjectCommand}});
 await assert.rejects(async()=>{for await(const _ of adapter.readObject({bucket:R2_SOURCE_BUCKET,path})){}},/stream unavailable/);
});
