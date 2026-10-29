import {test} from 'node:test';
import assert from 'node:assert/strict';
import {processSourceDocument} from './ai-source-pipeline.mjs';
const pages=[{physicalPage:1,text:'Airway management and capnography. '.repeat(20)}];

test('successful processing saves chunks before ready',async()=>{
 const steps=[];
 const result=await processSourceDocument({
  documentId:'book-1',loadPages:async()=>{steps.push('load');return pages},
  saveChunks:async(_id,chunks)=>{assert.ok(chunks.length);steps.push('save')},
  setStatus:async(_id,status)=>steps.push(status)
 });
 assert.equal(result.status,'ready');
 assert.deepEqual(steps,['extracting','load','indexing','save','ready']);
});
test('bad extraction never reaches ready',async()=>{
 const steps=[];
 await assert.rejects(processSourceDocument({
  documentId:'book-1',loadPages:async()=>[{physicalPage:1,text:' '}],
  saveChunks:async()=>steps.push('save'),
  setStatus:async(_id,status)=>steps.push(status)
 }),/OCR/);
 assert.deepEqual(steps,['extracting','failed']);
});
test('failed storage write never reaches ready',async()=>{
 const steps=[];
 await assert.rejects(processSourceDocument({
  documentId:'book-1',loadPages:async()=>pages,
  saveChunks:async()=>{throw Error('database offline')},
  setStatus:async(_id,status)=>steps.push(status)
 }),/database offline/);
 assert.deepEqual(steps,['extracting','indexing','failed']);
});
test('adapter functions are mandatory',async()=>{
 await assert.rejects(processSourceDocument({documentId:'book-1'}),TypeError);
});
