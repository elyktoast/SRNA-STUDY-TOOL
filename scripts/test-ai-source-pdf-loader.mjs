import {test} from 'node:test';
import assert from 'node:assert/strict';
import {loadSourcePdf} from './ai-source-pdf-loader.mjs';

test('loads PDF bytes, extracts pages and releases document',async()=>{
 let destroyed=false;
 const doc={numPages:1,getPage:async()=>({getTextContent:async()=>({items:[{str:'Capnography and airway monitoring'}]})}),destroy:async()=>{destroyed=true}};
 const result=await loadSourcePdf(new Uint8Array([37,80,68,70]),{getDocument:()=>({promise:Promise.resolve(doc)})});
 assert.equal(result.pages[0].physicalPage,1);
 assert.equal(result.ocrPages.length,0);
 assert.equal(destroyed,true);
});
test('rejects empty bytes and missing loader',async()=>{
 await assert.rejects(loadSourcePdf(new Uint8Array()),TypeError);
 await assert.rejects(loadSourcePdf(new Uint8Array([1])),TypeError);
});
test('releases PDF even when page extraction fails',async()=>{
 let destroyed=false;
 const doc={numPages:1,getPage:async()=>{throw Error('corrupt page')},destroy:async()=>{destroyed=true}};
 await assert.rejects(loadSourcePdf(new Uint8Array([1]),{getDocument:()=>({promise:Promise.resolve(doc)})}),/corrupt page/);
 assert.equal(destroyed,true);
});
