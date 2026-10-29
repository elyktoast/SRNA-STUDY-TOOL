import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceHttpHandler} from './ai-source-http-handler.mjs';
test('session provider failure is sanitized',async()=>{
 const handle=createSourceHttpHandler({
  workflow:{upload:async()=>{},process:async()=>{}},
  getAuthenticatedActor:async()=>{throw Error('token=private-value')}
 });
 const response=await handle({method:'POST',path:'/source/process',body:{documentId:'book'}});
 assert.equal(response.status,500);
 assert.doesNotMatch(JSON.stringify(response),/token|private-value/i);
});
