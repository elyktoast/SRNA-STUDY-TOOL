import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceUploadFinalizer} from './ai-source-upload-intent-db.mjs';
const id='01234567-89ab-4def-8abc-0123456789ab';
const path='documents/'+id+'.pdf';
const intent={storage_path:path,storage_bucket:'srna-private-textbooks',file_bytes:330000000};
const input={uploadId:id,actorId:'admin',intent,sha256:'a'.repeat(64),fileBytes:330000000,mimeType:'application/pdf'};
function harness({status='verifying',failUpdate=false}={}){
 const statements=[];let released=false;
 const client={query:async(sql)=>{
  statements.push(sql);
  if(sql==='BEGIN'||sql==='COMMIT'||sql==='ROLLBACK')return {};
  if(sql.includes('from private.ai_source_upload_intents')&&sql.includes('for update'))
   return {rows:[{id,title:'Book',file_bytes:330000000,mime_type:'application/pdf',storage_bucket:'srna-private-textbooks',storage_path:path,status,document_id:null}]};
  if(sql.includes('insert into private.ai_source_documents'))
   return {rows:[{id:'doc-1',processing_status:'uploaded'}]};
  if(sql.includes('update private.ai_source_upload_intents'))
   return {rowCount:failUpdate?0:1};
  throw new Error('unexpected query');
 },release:()=>{released=true}};
 return {db:{connect:async()=>client},statements,get released(){return released}};
}
test('registers verified PDF and commits atomically',async()=>{
 const h=harness();const result=await createSourceUploadFinalizer(h.db)(input);
 assert.equal(result.id,'doc-1');
 assert.equal(h.statements.at(-1),'COMMIT');
 assert.equal(h.released,true);
});
test('rejects non-verifying upload and rolls back',async()=>{
 const h=harness({status:'uploading'});
 await assert.rejects(createSourceUploadFinalizer(h.db)(input),/not eligible/);
 assert.equal(h.statements.at(-1),'ROLLBACK');
 assert.equal(h.released,true);
});
test('rolls back when linking document fails',async()=>{
 const h=harness({failUpdate:true});
 await assert.rejects(createSourceUploadFinalizer(h.db)(input),/conflict/);
 assert.equal(h.statements.at(-1),'ROLLBACK');
});
test('rejects malformed digest before connecting',async()=>{
 let connected=false;
 await assert.rejects(createSourceUploadFinalizer({connect:async()=>{connected=true}})({...input,sha256:'invalid'}),/invalid verified/);
 assert.equal(connected,false);
});
