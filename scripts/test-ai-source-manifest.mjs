import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildSourceManifest} from './ai-source-manifest.mjs';

test('manifest retains source and physical page mapping',()=>{
 const input={documentId:'book-1',pages:[
  {physicalPage:7,printedPage:'1',sectionHeading:'Airway',text:'Difficult airway assessment'},
  {physicalPage:8,printedPage:'2',sectionHeading:'Airway',text:'Laryngoscopy technique'}
 ]};
 const result=buildSourceManifest(input);
 assert.equal(result.pagesSeen,2);
 assert.equal(result.chunks.length,2);
 assert.equal(result.chunks[0].pageStart,7);
 assert.equal(result.chunks[1].pageEnd,8);
 assert.match(result.chunks[0].contentHash,/^[a-f0-9]{64}$/);
 assert.deepEqual(result,buildSourceManifest(input));
});
test('empty extraction requires OCR rather than ready status',()=>{
 assert.throws(()=>buildSourceManifest({documentId:'book-2',pages:[{physicalPage:1,text:' '}]}),/OCR/);
});
test('document identity is mandatory',()=>{
 assert.throws(()=>buildSourceManifest({documentId:'',pages:[]}),TypeError);
});
