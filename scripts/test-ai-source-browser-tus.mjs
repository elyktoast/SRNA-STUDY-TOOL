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
 const result=await uploadSourcePdfWithTus({file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',tus:m.tus,progress:v=>{progress=v}});
 assert.equal(result.uploadId,id);
 assert.equal(m.options.chunkSize,6291456);
 assert.equal(m.options.metadata.objectName,'documents/'+id+'.pdf');
 assert.equal(m.options.headers.authorization,'Bearer user-token');
 assert.equal(progress.bytesUploaded,file.size);
});
test('rejects mismatched intent before TUS starts',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({file,upload:{...upload,fileBytes:5},projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',tus:m.tus}),/does not match/);
 assert.equal(m.options,undefined);
});
test('rejects absent user token',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({file,upload,projectId:'xqyasyambwdyhsjkftqu',accessToken:'',tus:m.tus}),/token required/);
});

test('rejects pending intent before sending PDF bytes',async()=>{
 const m=mock();
 await assert.rejects(uploadSourcePdfWithTus({file,upload:{...upload,status:'pending'},projectId:'xqyasyambwdyhsjkftqu',accessToken:'user-token',tus:m.tus}),/does not match/);
 assert.equal(m.options,undefined);
});
