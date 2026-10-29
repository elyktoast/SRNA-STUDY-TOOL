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
   method:'POST',headers:{'x-source-title':'Book','content-type':'application/pdf'},body:new Uint8Array([37,80,68,70,45,49,46,55])
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

test('Node adapter rejects declared oversized PDF without calling upload',async()=>{
 let invoked=false;
 const server=createSourceNodeServer({maxBytes:8,
  workflow:{upload:async()=>{invoked=true},process:async()=>{}},
  getAuthenticatedActor:async()=> 'verified-admin'
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/upload',{
   method:'POST',headers:{'x-source-title':'Book','content-type':'application/pdf'},body:new Uint8Array(9)
  });
  assert.equal(response.status,413);
  assert.equal(invoked,false);
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('Node adapter rejects malformed JSON before processing',async()=>{
 let called=false;
 const server=createSourceNodeServer({workflow:{upload:async()=>{},process:async()=>{called=true}},getAuthenticatedActor:async()=> 'verified-admin'});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/process',{method:'POST',headers:{'content-type':'application/json'},body:'{' });
  assert.equal(response.status,400);
  assert.equal(called,false);
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('library GET endpoints use the authenticated actor and return private summaries',async()=>{
 const actors=[];
 const server=createSourceNodeServer({
  workflow:{
   upload:async()=>{},process:async()=>{},
   list:async({actorId})=>{actors.push(actorId);return [{id:'book',title:'Example'}]},
   detail:async({actorId,documentId})=>{actors.push(actorId);return documentId==='book'?{pageCount:2,chunkCount:4,passages:[]}:null}
  },
  getAuthenticatedActor:async()=> 'verified-admin'
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const base='http://127.0.0.1:'+server.address().port;
  const listing=await fetch(base+'/source/documents');
  assert.equal(listing.status,200);
  assert.equal((await listing.json()).documents[0].title,'Example');
  const detail=await fetch(base+'/source/detail?id=book');
  assert.equal(detail.status,200);
  assert.equal((await detail.json()).chunkCount,4);
  const missing=await fetch(base+'/source/detail?id=missing');
  assert.equal(missing.status,404);
  assert.deepEqual(actors,['verified-admin','verified-admin','verified-admin']);
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('unauthenticated library GET cannot access document metadata',async()=>{
 let accessed=false;
 const server=createSourceNodeServer({
  workflow:{upload:async()=>{},process:async()=>{},list:async()=>{accessed=true},detail:async()=>{accessed=true}},
  getAuthenticatedActor:async()=>null
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const response=await fetch('http://127.0.0.1:'+server.address().port+'/source/documents');
  assert.equal(response.status,401);
  assert.equal(accessed,false);
 }finally{await new Promise(resolve=>server.close(resolve))}
});

test('multipart completion accepts bounded 42-part JSON metadata while other endpoints retain 8 KiB limit',async()=>{
 let calls=0;
 const server=createSourceNodeServer({
  workflow:{upload:async()=>{},process:async()=>{}},
  getAuthenticatedActor:async()=> 'verified-admin',
  uploadRoutes:async()=>{calls++;return {status:200,body:{completed:true}}}
 });
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const base='http://127.0.0.1:'+server.address().port;
  const body=JSON.stringify({uploadId:'22222222-2222-4222-8222-222222222222',
   multipartId:'session',parts:Array.from({length:42},(_,i)=>({PartNumber:i+1,ETag:'a'.repeat(256)}))});
  assert.ok(Buffer.byteLength(body)>8192);
  assert.ok(Buffer.byteLength(body)<32768);
  const headers={'content-type':'application/json'};
  const complete=await fetch(base+'/source/uploads/r2/complete',{method:'POST',headers,body});
  assert.equal(complete.status,200);
  const sign=await fetch(base+'/source/uploads/r2/sign',{method:'POST',headers,body});
  assert.equal(sign.status,413);
  assert.equal(calls,1);
 }finally{await new Promise(resolve=>server.close(resolve))}
});
