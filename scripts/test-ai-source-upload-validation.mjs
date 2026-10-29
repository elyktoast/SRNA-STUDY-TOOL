import {test} from 'node:test';
import assert from 'node:assert/strict';
import {validateSourceUpload} from './ai-source-upload-validation.mjs';
const pdf=new Uint8Array([37,80,68,70,45,49,46,55,10]);
test('valid PDF returns metadata and checksum',()=>{
 const m=validateSourceUpload(pdf,'  Nurse Anesthesia  ');
 assert.equal(m.title,'Nurse Anesthesia');
 assert.equal(m.fileBytes,pdf.length);
 assert.match(m.sha256,/^[a-f0-9]{64}$/);
});
test('rejects fake PDFs and oversized files',()=>{
 assert.throws(()=>validateSourceUpload(new Uint8Array(10),'Book'),/signature/);
 assert.throws(()=>validateSourceUpload(pdf,'Book',{maxBytes:8}),/upload limit/);
});
test('rejects missing title and empty files',()=>{
 assert.throws(()=>validateSourceUpload(pdf,' '),/title/);
 assert.throws(()=>validateSourceUpload(new Uint8Array(), 'Book'),TypeError);
});
