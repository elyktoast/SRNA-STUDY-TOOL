import {test} from 'node:test';
import assert from 'node:assert/strict';
import {uploadPdfToR2} from './ai-source-browser-r2.mjs';
import {R2_PART_BYTES} from './ai-source-r2-upload-config.mjs';
const uploadId='22222222-2222-4222-8222-222222222222';
const etag='"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"';
function makeFile(){return {size:R2_PART_BYTES+8,type:'application/pdf',slice:(a,b)=>({start:a,end:b})};}
test('resumed upload skips confirmed first part and completes ordered inventory',async()=>{
 const paths=[],sent=[],progress=[];
 const request=async(path,body)=>{
  paths.push(path);
  if(path.endsWith('/create'))return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+8};
  if(path.endsWith('/parts'))return {parts:[{PartNumber:1,ETag:etag}]};
  if(path.endsWith('/sign')){assert.equal(body.partNumber,2);return {url:'https://r2.example/part'};}
  if(path.endsWith('/complete')){sent.push(body.parts);return {completed:true};}
  throw new Error('unexpected request');
 };
 let uploads=0;
 const fetchPart=async()=>{uploads++;return {ok:true,headers:{get:()=>etag}}};
 await uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart,progress:x=>progress.push(x)});
 assert.equal(uploads,1);
 assert.deepEqual(sent[0].map(x=>x.PartNumber),[1,2]);
 assert.equal(progress.at(-1).bytesUploaded,R2_PART_BYTES+8);
 assert.equal(paths.includes('/source/uploads/r2/abort'),false);
});
test('transient transfer failure preserves R2 session for retry',async()=>{
 const paths=[];
 const request=async(path)=>{
  paths.push(path);
  if(path.endsWith('/create'))return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+8};
  if(path.endsWith('/parts'))return {parts:[]};
  if(path.endsWith('/sign'))return {url:'https://r2.example/part'};
  throw new Error('unexpected request');
 };
 await assert.rejects(uploadPdfToR2({file:makeFile(),uploadId,request,concurrency:1,fetchPart:async()=>{throw new Error('network failed')}}),/network failed/);
 assert.equal(paths.includes('/source/uploads/r2/abort'),false);
});

test('failed part retries with a freshly signed URL',async()=>{
 let signs=0,attempts=0;
 const request=async(path,body)=>{
  if(path.endsWith('/create'))return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+8};
  if(path.endsWith('/parts'))return {parts:[{PartNumber:1,ETag:etag}]};
  if(path.endsWith('/sign'))return {url:'https://r2.example/part-'+(++signs)};
  if(path.endsWith('/complete'))return {completed:true};
  throw new Error('unexpected request');
 };
 const fetchPart=async(url)=>{
  attempts++;
  assert.equal(url,'https://r2.example/part-'+attempts);
  return {ok:attempts===2,headers:{get:()=>etag}};
 };
 await uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart,concurrency:1});
 assert.equal(signs,2);
 assert.equal(attempts,2);
});
