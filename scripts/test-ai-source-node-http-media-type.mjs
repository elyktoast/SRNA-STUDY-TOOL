import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createSourceNodeServer} from './ai-source-node-http.mjs';

test('process endpoint rejects non-JSON bodies before authentication',async()=>{
 let authenticated=false;
 const server=createSourceNodeServer({workflow:{upload:async()=>{},process:async()=>{}},getAuthenticatedActor:async()=>{authenticated=true;return 'actor'}});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 try{
  const address=server.address();
  const response=await fetch('http://127.0.0.1:'+address.port+'/source/process',{method:'POST',headers:{'content-type':'text/plain'},body:'not JSON'});
  assert.equal(response.status,415);
  assert.equal(authenticated,false);
 }finally{await new Promise(resolve=>server.close(resolve))}
});
