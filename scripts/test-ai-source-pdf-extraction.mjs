import {test} from 'node:test';
import assert from 'node:assert/strict';
import {extractPdfPages} from './ai-source-pdf-extraction.mjs';
test('extracts physical page numbers and identifies scanned pages',async()=>{
 const pdf={numPages:2,async getPage(n){
  return {async getTextContent(){return {items:n===1?[{str:'A textbook page with enough text to index.'}]:[]}}};
 }};
 const r=await extractPdfPages(pdf);
 assert.deepEqual(r.pages.map(x=>x.physicalPage),[1,2]);
 assert.deepEqual(r.ocrPages,[2]);
});
test('rejects invalid PDF adapters',async()=>{
 await assert.rejects(extractPdfPages({numPages:0}),TypeError);
});
test('rejects malformed text items',async()=>{
 await assert.rejects(extractPdfPages({numPages:1,getPage:async()=>({getTextContent:async()=>({})})}),/invalid page text/);
});
