import {test} from 'node:test';
import assert from 'node:assert/strict';
import {buildSourceManifest} from './ai-source-manifest.mjs';
import {validateSourceManifest} from './ai-source-ingestion-checks.mjs';

const manifest=()=>buildSourceManifest({documentId:'book-1',pages:[
 {physicalPage:1,text:'Capnography and end tidal carbon dioxide monitoring. '.repeat(10)},
 {physicalPage:2,text:'Ventilation and anesthetic circuit monitoring. '.repeat(10)}
]});
test('complete indexed pages pass validation',()=>{
 const result=validateSourceManifest(manifest());
 assert.equal(result.ok,true,JSON.stringify(result.errors));
});
test('missing text requires OCR or review',()=>{
 const m=buildSourceManifest({documentId:'book-1',pages:[{physicalPage:1,text:'tiny'}]});
 assert.equal(validateSourceManifest(m).ok,false);
});
test('mismatched source and out of order pages fail',()=>{
 const m=manifest();
 m.chunks[1].documentId='other';
 m.chunks[1].pageStart=1;
 assert.equal(validateSourceManifest(m).ok,false);
});
test('corrupt hashes and chunk order fail',()=>{
 const m=manifest();
 m.chunks[0].contentHash='bad';
 m.chunks[0].chunkOrder=3;
 assert.equal(validateSourceManifest(m).ok,false);
});

test('tampered passage is rejected even when hash is syntactically valid',()=>{
 const m=manifest();
 m.chunks[0].content+=' unauthorized modification';
 const result=validateSourceManifest(m);
 assert.equal(result.ok,false);
 assert.ok(result.errors.some(e=>e.includes('content hash mismatch')));
});
