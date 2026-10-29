import {test} from 'node:test';
import assert from 'node:assert/strict';
import {processAdminSourceDocument} from './ai-source-admin-service.mjs';
test('denied users cannot read or write textbook sources',async()=>{
 let called=false;
 await assert.rejects(processAdminSourceDocument({
  documentId:'book-1',actorId:'student',
  authorizeAdmin:async()=>false,
  loadPages:async()=>{called=true},
  saveChunks:async()=>{called=true},
  setStatus:async()=>{called=true}
 }),/access denied/);
 assert.equal(called,false);
});
test('missing server authorization is rejected',async()=>{
 await assert.rejects(processAdminSourceDocument({documentId:'book-1',actorId:'student'}),TypeError);
});
test('authorized user can execute processing',async()=>{
 const statuses=[];
 const result=await processAdminSourceDocument({
  documentId:'book-1',actorId:'admin',
  authorizeAdmin:async id=>id==='admin',
  loadPages:async()=>[{physicalPage:1,text:'Anesthesia monitoring and airway safety. '.repeat(20)}],
  saveChunks:async()=>{},
  setStatus:async(_id,status)=>statuses.push(status)
 });
 assert.equal(result.status,'ready');
 assert.deepEqual(statuses,['extracting','indexing','ready']);
});
