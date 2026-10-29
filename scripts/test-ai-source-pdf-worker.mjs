import {test} from 'node:test';
import assert from 'node:assert/strict';
import {processAdminPdf} from './ai-source-pdf-worker.mjs';

const getDocument=()=>({promise:Promise.resolve({
 numPages:2,
 getPage:async n=>({getTextContent:async()=>({items:n===1?[{str:'Airway assessment and carbon dioxide monitoring. '.repeat(12)}]:[]})}),
 destroy:async()=>{}
})});
const base=()=>({
 documentId:'book-1',actorId:'admin',authorizeAdmin:async()=>true,
 readPrivatePdf:async()=>new Uint8Array([37,80,68,70]),
 getDocument,ocrPage:async()=> 'Scanned anesthesia equipment material. '.repeat(12),
 saveChunks:async()=>{},setStatus:async()=>{}
});
test('PDF worker indexes both extracted and OCR pages',async()=>{
 const args=base();let chunks;
 args.saveChunks=async(_id,records)=>{chunks=records};
 const result=await processAdminPdf(args);
 assert.equal(result.status,'ready');
 assert.deepEqual([...new Set(chunks.map(c=>c.pageStart))],[1,2]);
 assert.equal(chunks.find(c=>c.pageStart===2).extractionMethod,'ocr');
});
test('missing OCR never marks textbook ready',async()=>{
 const args=base();delete args.ocrPage;
 const states=[];args.setStatus=async(_id,s)=>states.push(s);
 await assert.rejects(processAdminPdf(args),/OCR required/);
 assert.deepEqual(states,['extracting','failed']);
});
test('unauthorized actor never reads private PDF',async()=>{
 const args=base();args.authorizeAdmin=async()=>false;
 let accessed=false;args.readPrivatePdf=async()=>{accessed=true};
 await assert.rejects(processAdminPdf(args),/access denied/);
 assert.equal(accessed,false);
});
