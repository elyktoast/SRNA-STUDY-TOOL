import test from 'node:test';
import assert from 'node:assert/strict';
import {stagingReadOnlyRetry} from './staging-read-only-retry.mjs';
test('a reset lecture planning connection retries the same read-only operation',async()=>{
 let calls=0;const waits=[];
 const result=await stagingReadOnlyRetry('/generation/lecture-file-plan',async()=>{
  if(++calls<3)throw TypeError('fetch failed');return {database_writes:false,count:3};
 },{wait:async ms=>waits.push(ms)});
 assert.equal(result.count,3);assert.equal(calls,3);assert.deepEqual(waits,[1000,2000]);
});
test('paid generation and unknown endpoints are never retried, even on disconnect',async()=>{
 for(const path of ['/generation/one','/generation/approve','/generation/drafts/one','/generation/unknown']){
  let calls=0;await assert.rejects(stagingReadOnlyRetry(path,async()=>{calls++;throw TypeError('fetch failed');}),/fetch failed/);assert.equal(calls,1);
 }
});
test('read-only retries stop on validation, authentication, rate limits and server bugs',async()=>{
 for(const status of [400,401,403,409,422,429,500]){
  let calls=0;const error=Object.assign(Error('rejected'),{status});
  await assert.rejects(stagingReadOnlyRetry('/generation/preflight',async()=>{calls++;throw error;}),e=>e===error);assert.equal(calls,1);
 }
});
test('temporary read-only service failures are bounded to three attempts',async()=>{
 for(const status of [502,503,504]){
  let calls=0;const error=Object.assign(Error('unavailable'),{status});
  await assert.rejects(stagingReadOnlyRetry('/generation/preflight',async()=>{calls++;throw error;},{wait:async()=>{}}),e=>e===error);assert.equal(calls,3);
 }
});
