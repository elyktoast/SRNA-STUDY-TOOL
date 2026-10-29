import {test} from 'node:test';
import assert from 'node:assert/strict';
import {submitSourceTextbook} from './ai-source-upload-orchestrator.mjs';
import {R2_PART_BYTES} from './ai-source-r2-upload-config.mjs';

const id='01234567-89ab-4def-8abc-0123456789ab';
const etag='"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"';
const file={name:'Nurse Anesthesia.pdf',size:R2_PART_BYTES+8,type:'application/pdf',
 slice:(start,end)=>({start,end})};

function setup({startStatus='uploading',verifyId=id,resume=false}={}){
 const calls=[];
 const request=async(path,body)=>{
  calls.push({path,body});
  if(path.endsWith('/initiate'))return {upload:{uploadId:id,fileBytes:file.size,status:'pending'}};
  if(path.endsWith('/start'))return {status:startStatus};
  if(path.endsWith('/r2/create'))return {multipartId:'r2-session',partBytes:R2_PART_BYTES,fileBytes:file.size,title:file.name};
  if(path.endsWith('/r2/parts'))return {parts:resume?[{PartNumber:1,ETag:etag}]:[]};
  if(path.endsWith('/r2/sign'))return {url:'https://r2.example/upload'};
  if(path.endsWith('/r2/complete'))return {completed:true};
  if(path.endsWith('/verify'))return {result:{uploadId:verifyId,document:{id:'document-1'}}};
  throw new Error('unexpected route '+path);
 };
 let transfers=0;
 const fetchPart=async()=>{transfers++;return {ok:true,headers:{get:()=>etag}}};
 return {calls,request,fetchPart,transfers:()=>transfers};
}
test('initiates, transfers R2 parts, completes, then verifies textbook',async()=>{
 const h=setup();
 const doc=await submitSourceTextbook({file,request:h.request,fetchPart:h.fetchPart});
 assert.equal(doc.id,'document-1');
 assert.deepEqual(h.calls.map(x=>x.path),[
  '/source/uploads/initiate','/source/uploads/start','/source/uploads/r2/create',
  '/source/uploads/r2/parts','/source/uploads/r2/sign','/source/uploads/r2/sign',
  '/source/uploads/r2/complete','/source/uploads/verify'
 ]);
 assert.equal(h.transfers(),2);
 assert.equal(h.calls[0].body.fileBytes,file.size);
});
test('resumed R2 upload skips new intent and already transferred part',async()=>{
 const h=setup({resume:true});
 const doc=await submitSourceTextbook({file,request:h.request,fetchPart:h.fetchPart,resumeUploadId:id});
 assert.equal(doc.id,'document-1');
 assert.equal(h.transfers(),1);
 assert.equal(h.calls.some(x=>x.path.endsWith('/initiate')||x.path.endsWith('/start')),false);
});
test('does not transfer or verify if session start fails',async()=>{
 const h=setup({startStatus:'pending'});
 await assert.rejects(submitSourceTextbook({file,request:h.request,fetchPart:h.fetchPart}),/could not start/);
 assert.equal(h.calls.length,2);
});
test('rejects verification response for another upload',async()=>{
 const h=setup({verifyId:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'});
 await assert.rejects(submitSourceTextbook({file,request:h.request,fetchPart:h.fetchPart}),/verification did not complete/);
});
test('rejects invalid files before initiating upload',async()=>{
 for(const bad of [{...file,size:524288001},{...file,size:0},{...file,type:'application/octet-stream'}]){
  const h=setup();
  await assert.rejects(submitSourceTextbook({file:bad,request:h.request,fetchPart:h.fetchPart}),/invalid PDF file/);
  assert.equal(h.calls.length,0);
 }
});
test('rejects oversized PDF title before creating intent',async()=>{
 const h=setup();
 await assert.rejects(submitSourceTextbook({file:{...file,name:'a'.repeat(251)},request:h.request,fetchPart:h.fetchPart}),/invalid PDF title/);
 assert.equal(h.calls.length,0);
});
test('trims PDF title when initiating upload',async()=>{
 const h=setup();
 await submitSourceTextbook({file:{...file,name:'  Nurse Anesthesia.pdf  '},request:h.request,fetchPart:h.fetchPart});
 assert.equal(h.calls[0].body.title,'Nurse Anesthesia.pdf');
});

test('completed R2 session resumes directly to verification',async()=>{
 const calls=[];
 const request=async(path)=>{
  calls.push(path);
  if(path.endsWith('/r2/create'))return {completed:true,fileBytes:file.size,title:file.name};
  if(path.endsWith('/verify'))return {result:{uploadId:id,document:{id:'document-1'}}};
  throw new Error('unexpected route');
 };
 const document=await submitSourceTextbook({file,request,resumeUploadId:id,
  fetchPart:async()=>{throw new Error('no part transfer expected')}});
 assert.equal(document.id,'document-1');
 assert.deepEqual(calls,['/source/uploads/r2/create','/source/uploads/verify']);
});
