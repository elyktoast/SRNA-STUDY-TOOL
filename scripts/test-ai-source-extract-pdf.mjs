import {test} from 'node:test';
import assert from 'node:assert/strict';
import {extractPdfPages} from './ai-source-extract-pdf.mjs';

test('extracts physical pages and cleans up document',async()=>{
 let destroyed=false;
 const pdf={
  numPages:2,
  getPage:async n=>({
   getTextContent:async()=>({items:[{str:'Page '+n,hasEOL:true},{str:'Content'}]}),
   cleanup(){}
  }),
  destroy:async()=>{destroyed=true;}
 };
 const pages=await extractPdfPages(new Uint8Array([1]),{getDocument:()=>({promise:Promise.resolve(pdf)})});
 assert.deepEqual(pages,[
  {physicalPage:1,text:'Page 1\nContent'},
  {physicalPage:2,text:'Page 2\nContent'}
 ]);
 assert.equal(destroyed,true);
});
test('rejects empty PDF input',async()=>{
 await assert.rejects(extractPdfPages(new Uint8Array()),TypeError);
});
test('cleans up after extraction failure',async()=>{
 let destroyed=false;
 const pdf={numPages:1,getPage:async()=>{throw Error('corrupt page')},destroy:async()=>{destroyed=true}};
 await assert.rejects(extractPdfPages(new Uint8Array([1]),{getDocument:()=>({promise:Promise.resolve(pdf)})}),/corrupt page/);
 assert.equal(destroyed,true);
});
