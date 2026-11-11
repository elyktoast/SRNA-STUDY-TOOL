import test from 'node:test';
import assert from 'node:assert/strict';
import {isGenerationDisconnect,recoverCompletedGeneration} from '../equipment/assets/generation-completion-recovery.js';
const request={item_id:'fixed-item',topic:'original topic',textbook_id:'owned-book'};
const pending=()=>Object.assign(Error('not complete'),{rule:'CHECKPOINT_NOT_COMPLETE',status:409});
test('pending recovery never submits an authoring request and returns the completed result',async()=>{
 const calls=[],waits=[];const result={draft_id:'saved',published:false};
 const actual=await recoverCompletedGeneration(request,async body=>{calls.push(body);if(calls.length<3)throw pending();return result;},{attempts:3,intervalMs:1,wait:async ms=>waits.push(ms)});
 assert.equal(actual,result);assert.equal(calls.length,3);assert.equal(waits.length,2);
 for(const body of calls)assert.deepEqual(body,{...request,resume_completed_only:true});
 assert.equal(request.resume_completed_only,undefined);
});
test('a changed form cannot change the original request while recovering',async()=>{
 const original={...request};const calls=[];
 await recoverCompletedGeneration(original,async body=>{calls.push(body);if(calls.length===1)throw pending();return {};},{attempts:2,intervalMs:1,wait:async()=>{original.topic='changed topic';original.item_id='different-item';}});
 assert.equal(calls[1].item_id,request.item_id);assert.equal(calls[1].topic,request.topic);
});
test('recovery is bounded and never turns an incomplete checkpoint into paid generation',async()=>{
 const calls=[];await assert.rejects(recoverCompletedGeneration(request,async body=>{calls.push(body);throw pending();},{attempts:2,intervalMs:0,wait:async()=>{}}),/Check the draft bank/);
 assert.equal(calls.length,2);assert.ok(calls.every(body=>body.resume_completed_only===true));
});
test('authentication or validation failures stop immediately',async()=>{
 for(const status of [400,401,403,422]){let calls=0;const failure=Object.assign(Error('denied'),{status});
 await assert.rejects(recoverCompletedGeneration(request,async()=>{calls++;throw failure;},{wait:async()=>assert.fail('must not wait')}),error=>error===failure);assert.equal(calls,1);}
});
test('a disconnected recovery request can retry only the completed-only operation',async()=>{
 let calls=0;await recoverCompletedGeneration(request,async body=>{assert.equal(body.resume_completed_only,true);if(++calls===1)throw TypeError('fetch failed');return {};},{attempts:2,intervalMs:0,wait:async()=>{}});assert.equal(calls,2);
 assert.equal(isGenerationDisconnect(TypeError('fetch failed')),true);
 assert.equal(isGenerationDisconnect(Error('provider rejected')),false);assert.equal(isGenerationDisconnect(TypeError('Invalid URL')),false);
});
