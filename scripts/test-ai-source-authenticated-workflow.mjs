import {test} from 'node:test';
import assert from 'node:assert/strict';
import {bindSourceWorkflowToSession} from './ai-source-authenticated-workflow.mjs';
test('verified session identity overrides browser actor IDs',async()=>{
 const calls=[];
 const workflow={upload:async x=>{calls.push(x.actorId)},process:async x=>{calls.push(x.actorId)}};
 const secured=bindSourceWorkflowToSession(workflow,async()=> 'verified-admin');
 await secured.upload({actorId:'forged-admin'});
 await secured.process({actorId:'forged-admin'});
 assert.deepEqual(calls,['verified-admin','verified-admin']);
});
test('missing authentication prevents workflow access',async()=>{
 let accessed=false;
 const workflow={upload:async()=>{accessed=true},process:async()=>{accessed=true}};
 const secured=bindSourceWorkflowToSession(workflow,async()=>null);
 await assert.rejects(secured.upload({}),/authentication required/);
 assert.equal(accessed,false);
});
