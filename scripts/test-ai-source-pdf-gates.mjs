import {test} from 'node:test';
import assert from 'node:assert/strict';
import {extractPdfPages} from './ai-source-pdf-extraction.mjs';
import {resolveOcrPages} from './ai-source-ocr-gate.mjs';
const mockPdf=(texts)=>({numPages:texts.length,async getPage(n){return {async getTextContent(){return {items:[{str:texts[n-1]}]}}}}});
test('PDF extraction preserves physical page order',async()=>{
 const r=await extractPdfPages(mockPdf(['A sufficiently long first page','A sufficiently long second page']));
 assert.deepEqual(r.pages.map(p=>p.physicalPage),[1,2]);
 assert.deepEqual(r.ocrPages,[]);
});
test('scanned pages fail closed without OCR',async()=>{
 const r=await extractPdfPages(mockPdf(['A sufficiently long first page','']));
 await assert.rejects(resolveOcrPages(r),/OCR required/);
});
test('OCR replacement retains physical page number and provenance',async()=>{
 const r=await extractPdfPages(mockPdf(['']));
 const pages=await resolveOcrPages(r,{ocrPage:async n=>'Scanned page '+n+' has readable content'});
 assert.equal(pages[0].physicalPage,1);
 assert.equal(pages[0].extractionMethod,'ocr');
 assert.equal(pages[0].needsOcr,false);
});
test('empty OCR output is rejected',async()=>{
 const r=await extractPdfPages(mockPdf(['']));
 await assert.rejects(resolveOcrPages(r,{ocrPage:async()=>''}),/no usable text/);
});
test('invalid PDF and malformed page data reject',async()=>{
 await assert.rejects(extractPdfPages({numPages:0}),TypeError);
 await assert.rejects(extractPdfPages({numPages:1,getPage:async()=>({getTextContent:async()=>({items:null})})}),/invalid page text/);
});

test('OCR refuses a physical page mismatch',async()=>{
 const extraction={pages:[{physicalPage:2,text:'',needsOcr:true}],ocrPages:[1]};
 await assert.rejects(resolveOcrPages(extraction,{ocrPage:async()=> 'Readable scanned text'}),/invalid PDF page sequence/);
});

test('duplicate OCR page requests are rejected',async()=>{
 const extraction={pages:[{physicalPage:1,text:'',needsOcr:true}],ocrPages:[1,1]};
 await assert.rejects(resolveOcrPages(extraction,{ocrPage:async()=> 'Readable page text'}),/OCR page list mismatch/);
});

test('missing OCR request cannot silently skip a scanned page',async()=>{
 const extraction={pages:[{physicalPage:1,text:'',needsOcr:true}],ocrPages:[]};
 await assert.rejects(resolveOcrPages(extraction),/OCR page list mismatch/);
});
test('OCR rejects gaps in physical PDF page sequence',async()=>{
 const extraction={pages:[{physicalPage:1,text:'Long enough text to pass'},{physicalPage:3,text:'Another page with text'}],ocrPages:[]};
 await assert.rejects(resolveOcrPages(extraction),/invalid PDF page sequence/);
});

test('short OCR fragments cannot pass as a fully extracted page',async()=>{
 const extraction={pages:[{physicalPage:1,text:'',needsOcr:true}],ocrPages:[1]};
 await assert.rejects(resolveOcrPages(extraction,{ocrPage:async()=> 'one word'}),/no usable text/);
});
