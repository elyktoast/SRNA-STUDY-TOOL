import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceNodeServer} from './ai-source-node-http.mjs';
const workflow={upload:async()=>{},process:async()=>{}};
async function request(server,route,{method='POST',headers={},body={}}={}){
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const address=server.address();
  const response=await fetch('http://127.0.0.1:'+address.port+route,{
   method,headers:{'content-type':'application/json',...headers},body:JSON.stringify(body)});
  return {status:response.status,body:await response.json()};
 }finally{await new Promise(resolve=>server.close(resolve))}
}
test('session initiation reaches trusted route with resolved actor',async()=>{
 let received;
 const server=createSourceNodeServer({workflow,getAuthenticatedActor:async()=> 'admin',
  uploadRoutes:async args=>{received=args;return {status:201,body:{uploadId:'created'}}}});
 const result=await request(server,'/source/uploads/initiate',{body:{title:'Book'}});
 assert.equal(result.status,201);
 assert.equal(received.actorId,'admin');
 assert.equal(received.body.title,'Book');
});
test('upload route refuses unauthenticated callers',async()=>{
 let called=false;
 const server=createSourceNodeServer({workflow,getAuthenticatedActor:async()=>null,
  uploadRoutes:async()=>{called=true;return {status:200,body:{}}}});
 const result=await request(server,'/source/uploads/start');
 assert.equal(result.status,401);
 assert.equal(called,false);
});
test('session route refuses non-JSON content',async()=>{
 const server=createSourceNodeServer({workflow,getAuthenticatedActor:async()=> 'admin',
  uploadRoutes:async()=>({status:200,body:{}})});
 const result=await request(server,'/source/uploads/initiate',{headers:{'content-type':'text/plain'}});
 assert.equal(result.status,415);
});
test('upload session routes are not exposed when unconfigured',async()=>{
 const server=createSourceNodeServer({workflow,getAuthenticatedActor:async()=> 'admin'});
 const result=await request(server,'/source/uploads/initiate');
 assert.equal(result.status,404);
});
