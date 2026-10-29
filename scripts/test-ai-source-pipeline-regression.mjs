import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildSourceManifest} from './ai-source-manifest.mjs';
import {validateSourceManifest} from './ai-source-ingestion-checks.mjs';
import {processSourceDocument} from './ai-source-pipeline.mjs';
import {createSourceHttpHandler} from './ai-source-http-handler.mjs';

test('manifest has valid checksums and physical citations',()=>{
 const m=buildSourceManifest({documentId:'book',pages:Array.from({length:7},(_,i)=>({physicalPage:i+1,text:i===6?'Ventilation '.repeat(50):''}))});
 assert.equal(validateSourceManifest(m).ok,true);
 assert.equal(m.chunks[0].pageStart,7);
 assert.equal(m.chunks[0].pageEnd,7);
});
test('tampered source chunks cannot pass validation',()=>{
 const m=buildSourceManifest({documentId:'book',pages:[{physicalPage:1,text:'Ventilation '.repeat(50)}]});
 m.chunks[0].content='tampered';
 assert.equal(validateSourceManifest(m).ok,false);
});
test('failed indexing cannot mark document ready',async()=>{
 const statuses=[];
 await assert.rejects(processSourceDocument({
  documentId:'book',
  setStatus:async(id,s)=>statuses.push(s),
  loadPages:async()=>[{physicalPage:1,text:'Ventilation '.repeat(50)}],
  saveChunks:async()=>{throw new Error('database unavailable')}
 }),/database unavailable/);
 assert.deepEqual(statuses,['extracting','indexing','failed']);
});
test('successful indexing becomes ready only after saving',async()=>{
 const statuses=[];
 const result=await processSourceDocument({
  documentId:'book',
  setStatus:async(id,s)=>statuses.push(s),
  loadPages:async()=>[{physicalPage:1,text:'Ventilation '.repeat(50)}],
  saveChunks:async(id,chunks)=>assert.ok(chunks.length>0)
 });
 assert.equal(result.status,'ready');
 assert.deepEqual(statuses,['extracting','indexing','ready']);
});
test('unauthenticated requests never invoke privileged workflow',async()=>{
 let called=false;
 const handler=createSourceHttpHandler({
  workflow:{upload:async()=>{called=true},process:async()=>{called=true}},
  getAuthenticatedActor:async()=>null
 });
 const result=await handler({method:'POST',path:'/source/process',body:{documentId:'book'}});
 assert.equal(result.status,401);
 assert.equal(called,false);
});
test('unauthorized admin processing is forbidden',async()=>{
 const handler=createSourceHttpHandler({
  workflow:{upload:async()=>{},process:async()=>{throw new Error('source processing access denied')}},
  getAuthenticatedActor:async()=> 'user'
 });
 const result=await handler({method:'POST',path:'/source/process',body:{documentId:'book'}});
 assert.equal(result.status,403);
});

test('citations cannot point beyond the physical PDF page count',()=>{
 const m=buildSourceManifest({documentId:'book',pages:[{physicalPage:1,text:'Anesthesia '.repeat(50)}]});
 m.chunks[0].pageStart=2;
 m.chunks[0].pageEnd=2;
 assert.equal(validateSourceManifest(m).ok,false);
 assert.ok(validateSourceManifest(m).errors.some(e=>e.includes('page outside document')));
});
