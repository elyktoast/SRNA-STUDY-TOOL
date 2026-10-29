import {test} from 'node:test';
import assert from 'node:assert/strict';
import {submitSourceTextbook} from './ai-source-upload-orchestrator.mjs';
const id='01234567-89ab-4def-8abc-0123456789ab';
const file={name:'Nurse Anesthesia.pdf',size:330000000,type:'application/pdf'};
function setup({startStatus='uploading',verifyId=id}={}){
 const calls=[];let opts;
 class Upload{
  constructor(_file,options){opts=options}
  async findPreviousUploads(){return []}
  start(){opts.onSuccess()}
 }
 const request=async(path,body)=>{
  calls.push({path,body});
  if(path.endsWith('/initiate'))return {upload:{uploadId:id,fileBytes:file.size,status:'pending'}};
  if(path.endsWith('/start'))return {status:startStatus};
  if(path.endsWith('/verify'))return {result:{uploadId:verifyId,document:{id:'document-1'}}};
  throw new Error('unexpected route');
 };
 return {calls,request,tus:{Upload}};
}
test('initiates, transfers, then verifies textbook in order',async()=>{
 const h=setup();
 const doc=await submitSourceTextbook({file,request:h.request,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:h.tus});
 assert.equal(doc.id,'document-1');
 assert.deepEqual(h.calls.map(x=>x.path),['/source/uploads/initiate','/source/uploads/start','/source/uploads/verify']);
 assert.equal(h.calls[0].body.fileBytes,330000000);
});
test('does not transfer or verify if session start fails',async()=>{
 const h=setup({startStatus:'pending'});
 await assert.rejects(submitSourceTextbook({file,request:h.request,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:h.tus}),/could not start/);
 assert.equal(h.calls.length,2);
});
test('rejects verification response for another upload',async()=>{
 const h=setup({verifyId:'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'});
 await assert.rejects(submitSourceTextbook({file,request:h.request,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:h.tus}),/verification did not complete/);
});

test('rejects invalid files before initiating a server upload intent',async()=>{
 for(const bad of [
  {...file,size:524288001},
  {...file,size:0},
  {...file,type:'application/octet-stream'}
 ]){
  const h=setup();
  await assert.rejects(submitSourceTextbook({
   file:bad,request:h.request,projectId:'xqyasyambwdyhsjkftqu',
   accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:h.tus
  }),/invalid PDF file/);
  assert.equal(h.calls.length,0);
 }
});

test('rejects oversized PDF title before creating upload intent',async()=>{
 const h=setup();
 await assert.rejects(submitSourceTextbook({
  file:{...file,name:'a'.repeat(251)},request:h.request,
  projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',
  userId:'11111111-1111-4111-8111-111111111111',tus:h.tus
 }),/invalid PDF title/);
 assert.equal(h.calls.length,0);
});
test('trims PDF title before initiating upload',async()=>{
 const h=setup();
 await submitSourceTextbook({
  file:{...file,name:'  Nurse Anesthesia.pdf  '},request:h.request,
  projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',
  userId:'11111111-1111-4111-8111-111111111111',tus:h.tus
 });
 assert.equal(h.calls[0].body.title,'Nurse Anesthesia.pdf');
});
