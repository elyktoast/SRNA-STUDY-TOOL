import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createR2MultipartController} from './ai-source-r2-multipart.mjs';
const id='01234567-89ab-4def-8abc-0123456789ab';
const intent={id,storage_bucket:'srna-private-textbooks',storage_path:`documents/${id}.pdf`,file_bytes:25165824,status:'uploading'};
class CreateMultipartUploadCommand{constructor(input){this.input=input}}
class UploadPartCommand{constructor(input){this.input=input}}
class CompleteMultipartUploadCommand{constructor(input){this.input=input}}
class AbortMultipartUploadCommand{constructor(input){this.input=input}}
class ListPartsCommand{constructor(input){this.input=input}}
function fixture(){
 const calls=[];
 const client={async send(command){calls.push(command);if(command instanceof ListPartsCommand)return {Parts:[{PartNumber:1,ETag:'etag-one',Size:12582912}],IsTruncated:false};return {UploadId:'r2-multipart-session'}}};
 const presign=async(_client,command)=>{calls.push(command);return 'https://example.r2.cloudflarestorage.com/signed'};
 const controller=createR2MultipartController({client,presign,commands:{CreateMultipartUploadCommand,UploadPartCommand,CompleteMultipartUploadCommand,AbortMultipartUploadCommand,ListPartsCommand}});
 return {controller,calls};
}
test('starts multipart session only in private bucket',async()=>{
 const {controller,calls}=fixture();
 assert.equal((await controller.initiate(intent)).partBytes,12582912);
 assert.equal(calls[0].input.Bucket,'srna-private-textbooks');
 await assert.rejects(controller.initiate({...intent,storage_bucket:'other'}),/invalid active/);
});
test('signs only valid part numbers for expected file size',async()=>{
 const {controller}=fixture();
 assert.equal((await controller.signPart(intent,{multipartId:'r2-multipart-session',partNumber:2})).partNumber,2);
 await assert.rejects(controller.signPart(intent,{multipartId:'r2-multipart-session',partNumber:3}),/invalid R2 multipart part/);
});
test('refuses incomplete or untrusted multipart ETags',async()=>{
 const {controller,calls}=fixture();
 await assert.rejects(controller.complete(intent,{multipartId:'r2-multipart-session',parts:[{PartNumber:1,ETag:'bad\nvalue'}]}),/invalid R2 multipart completion/);
 assert.equal(calls.length,0);
});
test('completes ordered parts and supports explicit abort',async()=>{
 const {controller,calls}=fixture();
 const parts=[1,2].map(PartNumber=>({PartNumber,ETag:'a'.repeat(32)}));
 assert.deepEqual(await controller.complete(intent,{multipartId:'r2-multipart-session',parts}),{completed:true});
 assert.deepEqual(await controller.abort(intent,{multipartId:'r2-multipart-session'}),{aborted:true});
 assert.equal(calls[0] instanceof CompleteMultipartUploadCommand,true);
 assert.equal(calls[1] instanceof AbortMultipartUploadCommand,true);
});

test('recovers uploaded R2 parts with validated sizes',async()=>{
 const {controller}=fixture();
 const result=await controller.listParts(intent,{multipartId:'r2-multipart-session'});
 assert.deepEqual(result.parts,[{PartNumber:1,ETag:'etag-one'}]);
});

test('rejects a repeated R2 pagination marker',async()=>{
 let pages=0;
 const client={send:async(command)=>{
  if(!(command instanceof ListPartsCommand))throw new Error('unexpected command');
  pages++;
  return {Parts:[],IsTruncated:true,NextPartNumberMarker:1};
 }};
 const controller=createR2MultipartController({
  client,presign:async()=>'',commands:{CreateMultipartUploadCommand,UploadPartCommand,CompleteMultipartUploadCommand,AbortMultipartUploadCommand,ListPartsCommand}
 });
 await assert.rejects(controller.listParts(intent,{multipartId:'r2-multipart-session'}),/invalid R2 part pagination/);
 assert.equal(pages,2);
});

test('rejects an out-of-range pagination marker',async()=>{
 const client={send:async()=>({Parts:[],IsTruncated:true,NextPartNumberMarker:99})};
 const controller=createR2MultipartController({
  client,presign:async()=>'',commands:{CreateMultipartUploadCommand,UploadPartCommand,CompleteMultipartUploadCommand,AbortMultipartUploadCommand,ListPartsCommand}
 });
 await assert.rejects(controller.listParts(intent,{multipartId:'r2-multipart-session'}),/invalid R2 part pagination/);
});
