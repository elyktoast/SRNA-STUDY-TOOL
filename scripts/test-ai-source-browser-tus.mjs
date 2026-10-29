import {test} from 'node:test';
import assert from 'node:assert/strict';
import {uploadSourcePdfWithTus} from './ai-source-browser-tus.mjs';
const id='01234567-89ab-4def-8abc-0123456789ab';
const file={size:330000000,type:'application/pdf'};
const upload={uploadId:id,fileBytes:file.size,status:'uploading'};
function mock(){
 let options;
 class Upload{
  constructor(_file,opts){options=opts}
  async findPreviousUploads(){return []}
  start(){options.onProgress(file.size,file.size);options.onSuccess()}
 }
 return {tus:{Upload},get options(){return options}};
}
test('uploads with user JWT, fixed object path and six MiB chunks',async()=>{
 const m=mock();let progress;
 const result=await uploadSourcePdfWithTus({file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:m.tus,progress:v=>{progress=v}});
 assert.equal(result.uploadId,id);
 assert.equal(m.options.chunkSize,6291456);
 assert.equal(m.options.metadata.objectName,'documents/'+id+'.pdf');
 assert.equal(m.options.headers.authorization,'Bearer user-token');
 assert.equal(progress.bytesUploaded,file.size);
});
test('rejects mismatched intent before TUS starts',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({file,upload:{...upload,fileBytes:5},projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:m.tus}),/does not match/);
 assert.equal(m.options,undefined);
});
test('rejects absent user token',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'',tus:m.tus}),/token required/);
});

test('rejects pending intent before sending PDF bytes',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({file,upload:{...upload,status:'pending'},projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:m.tus}),/does not match/);
 assert.equal(m.options,undefined);
});

test('synchronous TUS constructor error rejects cleanly',async()=>{
 class Upload{constructor(){throw new Error('TUS initialization failed')}}
 await assert.rejects(uploadSourcePdfWithTus({
  file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:{Upload}
 }),/TUS initialization failed/);
});
test('already canceled upload does not initialize transport',async()=>{
 const m=mock();
 const controller=new AbortController();
 controller.abort();
 await assert.rejects(uploadSourcePdfWithTus({
  file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',
  tus:m.tus,signal:controller.signal
 }),/upload canceled/);
 assert.equal(m.options,undefined);
});

test('progress callback exceptions do not fail a successful transfer',async()=>{
 const m=mock();
 const result=await uploadSourcePdfWithTus({
  file,upload,projectId:'xqyasyambwdyhsjkftqu',
  accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:m.tus,
  progress:()=>{throw new Error('UI unmounted')}
 });
 assert.equal(result.bytes,file.size);
});
test('resume uses a previously recorded upload session',async()=>{
 let resumed=false,started=false,options;
 class Upload{
  constructor(_file,opts){options=opts}
  async findPreviousUploads(){return [{uploadUrl:'previous'}]}
  resumeFromPreviousUpload(previous){resumed=previous.uploadUrl==='previous'}
  start(){started=true;options.onSuccess()}
 }
 await uploadSourcePdfWithTus({
  file,upload,projectId:'xqyasyambwdyhsjkftqu',
  accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:{Upload}
 });
 assert.equal(resumed,true);
 assert.equal(started,true);
});

test('resumable fingerprint is isolated per user and intent',async()=>{
 const m=mock();
 await uploadSourcePdfWithTus({file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',userId:'11111111-1111-4111-8111-111111111111',tus:m.tus});
 const fingerprint=await m.options.fingerprint();
 assert.match(fingerprint,/11111111-1111-4111-8111-111111111111/);
 assert.match(fingerprint,/01234567-89ab-4def-8abc-0123456789ab/);
});

test('rejects invalid progress callback before constructing transport',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({
  file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',
  userId:'11111111-1111-4111-8111-111111111111',tus:m.tus,progress:'invalid'
 }),/progress callback required/);
 assert.equal(m.options,undefined);
});

test('reports valid incremental progress and ignores corrupt transport counters',async()=>{
 let options;
 class Upload{
  constructor(_file,opts){options=opts}
  async findPreviousUploads(){return []}
  start(){
   options.onProgress(6291456,file.size);
   options.onProgress(-1,file.size);
   options.onProgress(file.size+1,file.size);
   options.onProgress(file.size,file.size);
   options.onSuccess();
  }
 }
 const values=[];
 await uploadSourcePdfWithTus({
  file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',
  userId:'11111111-1111-4111-8111-111111111111',tus:{Upload},
  progress:value=>values.push(value.bytesUploaded)
 });
 assert.deepEqual(values,[6291456,file.size]);
});
