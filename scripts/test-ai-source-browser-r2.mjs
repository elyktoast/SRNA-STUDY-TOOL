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

test('rejects mismatched PDF size before recovering or uploading parts',async()=>{
 const paths=[];
 const request=async(path)=>{
  paths.push(path);
  return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+9};
 };
 await assert.rejects(uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart:async()=>{throw new Error('should not upload')}}),/PDF size does not match/);
 assert.deepEqual(paths,['/source/uploads/r2/create']);
});
test('rejects mismatched PDF title before transferring parts',async()=>{
 const file={...makeFile(),name:'different.pdf'};
 const request=async()=>({multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:file.size,title:'original.pdf'});
 await assert.rejects(uploadPdfToR2({file,uploadId,request,fetchPart:async()=>{throw new Error('should not upload')}}),/PDF title does not match/);
});

test('malformed recovered ETag prevents transfer',async()=>{
 let transfers=0;
 const request=async(path)=>{
  if(path.endsWith('/create'))return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+8};
  if(path.endsWith('/parts'))return {parts:[{PartNumber:1,ETag:'"unmatched'}]};
  throw new Error('unexpected request');
 };
 await assert.rejects(uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart:async()=>{transfers++}}),/invalid recovered R2 part/);
 assert.equal(transfers,0);
});

test('newline in recovered ETag is rejected before part transfer',async()=>{
 let transfers=0;
 const request=async(path)=>{
  if(path.endsWith('/create'))return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+8};
  if(path.endsWith('/parts'))return {parts:[{PartNumber:1,ETag:'bad\nvalue'}]};
  throw new Error('unexpected request');
 };
 await assert.rejects(uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart:async()=>{transfers++}}),/invalid recovered R2 part/);
 assert.equal(transfers,0);
});

test('completed R2 multipart resumes directly to verification without transfer',async()=>{
 const paths=[];
 const request=async(path)=>{
  paths.push(path);
  if(path.endsWith('/create'))return {completed:true,fileBytes:R2_PART_BYTES+8};
  throw new Error('unexpected multipart request');
 };
 const result=await uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart:async()=>{throw new Error('transfer should not run')}});
 assert.equal(result.uploadId,uploadId);
 assert.deepEqual(paths,['/source/uploads/r2/create']);
});

test('embedded quote in recovered ETag is rejected',async()=>{
 const request=async(path)=>{
  if(path.endsWith('/create'))return {multipartId:'session',partBytes:R2_PART_BYTES,fileBytes:R2_PART_BYTES+8};
  if(path.endsWith('/parts'))return {parts:[{PartNumber:1,ETag:'abc"def'}]};
  throw new Error('unexpected request');
 };
 await assert.rejects(uploadPdfToR2({file:makeFile(),uploadId,request,fetchPart:async()=>{throw new Error('should not transfer')}}),/invalid recovered R2 part/);
});
