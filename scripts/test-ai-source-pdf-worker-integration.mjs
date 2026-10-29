import {test} from 'node:test';
import assert from 'node:assert/strict';
import {processAdminPdf} from './ai-source-pdf-worker.mjs';

const getDocument=()=>({
 promise:Promise.resolve({
  numPages:2,
  async getPage(n){return {async getTextContent(){return {items:[{str:(n===1?'Anesthesia equipment safety requires checking the complete breathing circuit before each case. ':'Ventilator pressure alarms and disconnection monitoring support safe ventilation. ').repeat(4)}]}}}},
  async destroy(){}
 })
});

test('authorized two-page textbook is indexed with physical citations',async()=>{
 const statuses=[];
 let saved;
 const result=await processAdminPdf({
  documentId:'book',actorId:'admin',authorizeAdmin:async()=>true,
  readPrivatePdf:async()=>new Uint8Array([37,80,68,70,45]),
  getDocument,
  saveChunks:async(id,chunks)=>{saved=chunks;assert.equal(id,'book')},
  setStatus:async(id,status)=>statuses.push(status)
 });
 assert.equal(result.status,'ready');
 assert.deepEqual(statuses,['extracting','indexing','ready']);
 assert.deepEqual([...new Set(saved.map(c=>c.pageStart))],[1,2]);
 assert.ok(saved.every(c=>c.pageStart===c.pageEnd));
});

test('unauthorized processing never reads private textbook bytes',async()=>{
 let read=false;
 await assert.rejects(processAdminPdf({
  documentId:'book',actorId:'student',authorizeAdmin:async()=>false,
  readPrivatePdf:async()=>{read=true;return new Uint8Array([37,80,68,70,45])},
  getDocument,saveChunks:async()=>{},setStatus:async()=>{}
 }),/access denied/);
 assert.equal(read,false);
});

test('scanned textbook without OCR never becomes ready',async()=>{
 const statuses=[];
 await assert.rejects(processAdminPdf({
  documentId:'book',actorId:'admin',authorizeAdmin:async()=>true,
  readPrivatePdf:async()=>new Uint8Array([37,80,68,70,45]),
  getDocument:()=>({promise:Promise.resolve({
   numPages:1,async getPage(){return {async getTextContent(){return {items:[]}}}},
   async destroy(){}
  })}),
  saveChunks:async()=>{throw Error('must not save')},
  setStatus:async(id,status)=>statuses.push(status)
 }),/OCR required/);
 assert.deepEqual(statuses,['extracting','failed']);
});

test('PDF loading failure marks document failed without saving chunks',async()=>{
 const statuses=[];
 let saved=false;
 await assert.rejects(processAdminPdf({
  documentId:'book',actorId:'admin',authorizeAdmin:async()=>true,
  readPrivatePdf:async()=>new Uint8Array([37,80,68,70,45]),
  getDocument:()=>({promise:Promise.reject(new Error('corrupt PDF'))}),
  saveChunks:async()=>{saved=true},setStatus:async(id,status)=>statuses.push(status)
 }),/corrupt PDF/);
 assert.equal(saved,false);
 assert.deepEqual(statuses,['extracting','failed']);
});
