import {test} from 'node:test';
import assert from 'node:assert/strict';
import {verifyCompletedTextbook} from './ai-source-upload-completion.mjs';
const uploadId='01234567-89ab-4def-8abc-0123456789ab';
const pdf=new TextEncoder().encode('%PDF-1.7 sample');
const intent={storage_bucket:'ai-textbook-sources',storage_path:'documents/'+uploadId+'.pdf',file_bytes:pdf.length};
function setup(overrides={}){
 const calls=[];
 const options={actorId:'admin',uploadId,authorizeAdmin:async()=>true,
  claimVerification:async()=>intent,inspectObject:async()=>({size:pdf.length}),
  readObject:async function*(){yield pdf.subarray(0,2);yield pdf.subarray(2)},
  completeVerifiedIntent:async data=>{calls.push(data);return {id:'document'}},
  failVerification:async()=>{calls.push('failed')},...overrides};
 return {options,calls};
}
test('verifies streamed PDF and finalizes record',async()=>{
 const f=setup();
 const result=await verifyCompletedTextbook(f.options);
 assert.equal(result.document.id,'document');
 assert.equal(f.calls.length,1);
 assert.match(f.calls[0].sha256,/^[a-f0-9]{64}$/);
});
test('rejects unauthorized completion',async()=>{
 const f=setup({authorizeAdmin:async()=>false});
 await assert.rejects(verifyCompletedTextbook(f.options),/access denied/);
 assert.equal(f.calls.length,0);
});
test('rejects truncated stream',async()=>{
 const f=setup({readObject:async function*(){yield pdf.subarray(0,7)}});
 await assert.rejects(verifyCompletedTextbook(f.options),/length mismatch/);
 assert.deepEqual(f.calls,['failed']);
});
test('rejects incorrect PDF signature',async()=>{
 const f=setup({readObject:async function*(){yield new TextEncoder().encode('BAD!!'+new TextDecoder().decode(pdf.subarray(5)))}});
 await assert.rejects(verifyCompletedTextbook(f.options),/not a PDF/);
 assert.deepEqual(f.calls,['failed']);
});

test('accepts a numeric string size from Storage metadata',async()=>{
 const f=setup({inspectObject:async()=>({size:String(pdf.length)})});
 const result=await verifyCompletedTextbook(f.options);
 assert.equal(result.document.id,'document');
 assert.equal(f.calls.length,1);
});
test('rejects malformed Storage object size before reading',async()=>{
 const f=setup({inspectObject:async()=>({size:'unknown'})});
 await assert.rejects(verifyCompletedTextbook(f.options),/size mismatch/);
 assert.deepEqual(f.calls,['failed']);
});

test('rejects oversized stream chunks before hashing',async()=>{
 const f=setup({readObject:async function*(){yield new Uint8Array(6291457)}});
 await assert.rejects(verifyCompletedTextbook(f.options),/invalid upload stream chunk size/);
 assert.deepEqual(f.calls,['failed']);
});
test('rejects empty stream chunks',async()=>{
 const f=setup({readObject:async function*(){yield new Uint8Array(0)}});
 await assert.rejects(verifyCompletedTextbook(f.options),/invalid upload stream chunk size/);
 assert.deepEqual(f.calls,['failed']);
});
