import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceNodeServer} from './ai-source-node-http.mjs';
test('Node adapter accepts PDF bytes but ignores browser actor ID',async()=>{
 let observed;
 const server=createSourceNodeServer({
  workflow:{upload:async input=>{observed=input;return {id:'book-1'}},process:async()=>{}},
  getAuthenticatedActor:async()=> 'verified-admin'
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const url='http://127.0.0.1:'+server.address().port;
  const response=await fetch(url+'/source/upload',{method:'POST',headers:{'x-source-title':'Book','x-actor-id':'forged','content-type':'application/pdf'},body:new Uint8Array([37,80,68,70,45,49,46,55])});
  assert.equal(response.status,201);
  assert.equal(observed.actorId,'verified-admin');
  assert.equal(observed.title,'Book');
  assert.equal(observed.bytes.length,8);
 }finally{await new Promise(resolve=>server.close(resolve))}
});
test('Node adapter rejects missing session',async()=>{
 const server=createSourceNodeServer({
  workflow:{upload:async()=>{throw Error('must not run')},process:async()=>{}},
  getAuthenticatedActor:async()=>null
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/upload',{method:'POST',headers:{'x-source-title':'Book','content-type':'application/pdf'},body:new Uint8Array(8)});
  assert.equal(response.status,401);
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('Node adapter rejects unauthenticated request before consuming its body',async()=>{
 const server=createSourceNodeServer({
  workflow:{upload:async()=>{throw Error('must not upload')},process:async()=>{}},
  getAuthenticatedActor:async()=>null
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/upload',{
   method:'POST',headers:{'x-source-title':'Book','content-type':'application/pdf'},
   body:new Uint8Array(16)
  });
  assert.equal(response.status,401);
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('Node adapter verifies the session exactly once',async()=>{
 let calls=0;
 const server=createSourceNodeServer({
  workflow:{upload:async input=>({id:'book-2',actorId:input.actorId}),process:async()=>{}},
  getAuthenticatedActor:async()=>{calls++;return 'verified-admin'}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/upload',{
   method:'POST',headers:{'x-source-title':'Book'},body:new Uint8Array([37,80,68,70,45,49,46,55])
  });
  assert.equal(response.status,201);
  assert.equal(calls,1);
  assert.equal((await response.json()).document.actorId,'verified-admin');
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('Node adapter rejects non-PDF content types before upload',async()=>{
 let uploaded=false;
 const server=createSourceNodeServer({
  workflow:{upload:async()=>{uploaded=true},process:async()=>{}},
  getAuthenticatedActor:async()=> 'verified-admin'
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/upload',{
   method:'POST',headers:{'x-source-title':'Book','content-type':'text/plain'},body:'not a PDF'
  });
  assert.equal(response.status,415);
  assert.equal(uploaded,false);
 }finally{await new Promise(resolve=>server.close(resolve))}
});
