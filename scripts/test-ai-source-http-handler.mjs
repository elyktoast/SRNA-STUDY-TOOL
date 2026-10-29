import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceHttpHandler} from './ai-source-http-handler.mjs';
test('requires authenticated session before upload',async()=>{
 let invoked=false;
 const handle=createSourceHttpHandler({workflow:{upload:async()=>{invoked=true},process:async()=>{}},getAuthenticatedActor:async()=>null});
 const response=await handle({method:'POST',path:'/source/upload',body:{bytes:new Uint8Array(8)}});
 assert.equal(response.status,401);
 assert.equal(invoked,false);
});
test('verified session overrides forged browser actor',async()=>{
 let actor;
 const handle=createSourceHttpHandler({workflow:{upload:async input=>{actor=input.actorId;return {id:'book-1'}},process:async()=>{}},getAuthenticatedActor:async()=> 'real-admin'});
 const response=await handle({method:'POST',path:'/source/upload',body:{actorId:'fake-admin',title:'Book',bytes:new Uint8Array(8)}});
 assert.equal(response.status,201);
 assert.equal(actor,'real-admin');
});
test('denies non-admin and redacts internal failures',async()=>{
 const handle=createSourceHttpHandler({workflow:{upload:async()=>{throw Error('source upload access denied')},process:async()=>{throw Error('SQL password=secret')}},getAuthenticatedActor:async()=> 'student'});
 assert.equal((await handle({method:'POST',path:'/source/upload',body:{bytes:new Uint8Array(8)}})).status,403);
 const response=await handle({method:'POST',path:'/source/process',body:{documentId:'book-1'}});
 assert.equal(response.status,500);
 assert.doesNotMatch(JSON.stringify(response),/password|secret/i);
});
test('rejects oversized upload without calling storage',async()=>{
 let invoked=false;
 const handle=createSourceHttpHandler({workflow:{upload:async()=>{invoked=true},process:async()=>{}},getAuthenticatedActor:async()=> 'admin',maxBytes:8});
 assert.equal((await handle({method:'POST',path:'/source/upload',body:{bytes:new Uint8Array(9)}})).status,413);
 assert.equal(invoked,false);
});
