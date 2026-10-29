import {test} from 'node:test';
import assert from 'node:assert/strict';
import {resolveOcrPages} from './ai-source-ocr-gate.mjs';
const extraction={pages:[{physicalPage:1,text:'normal'},{physicalPage:2,text:'',needsOcr:true}],ocrPages:[2]};
test('missing OCR provider fails instead of silently skipping a page',async()=>{
 await assert.rejects(resolveOcrPages(extraction),/OCR required/);
});
test('OCR replaces only requested page and preserves numbering',async()=>{
 const pages=await resolveOcrPages(extraction,{ocrPage:async()=> 'scanned textbook content'});
 assert.equal(pages[0].text,'normal');
 assert.equal(pages[1].physicalPage,2);
 assert.equal(pages[1].text,'scanned textbook content');
 assert.equal(pages[1].extractionMethod,'ocr');
});
test('blank OCR response fails',async()=>{
 await assert.rejects(resolveOcrPages(extraction,{ocrPage:async()=>''}),/no usable text/);
});
