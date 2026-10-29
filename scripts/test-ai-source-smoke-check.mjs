import {test} from 'node:test';
import assert from 'node:assert/strict';
import {checkSourceApi} from './ai-source-smoke-check.mjs';
const args={baseUrl:'https://study.example',accessToken:'test-token'};
const response=(status,type='application/json')=>({status,ok:status>=200&&status<300,headers:{get:()=>type}});
test('source API smoke check confirms authenticated JSON response',async()=>{
 let url,options;
 const result=await checkSourceApi({...args,fetchImpl:async(u,o)=>{url=u;options=o;return response(200)}});
 assert.equal(result.ready,true);
 assert.equal(url,'https://study.example/source/documents');
 assert.equal(options.headers.authorization,'Bearer test-token');
});
test('source API smoke check distinguishes proxy and authorization failures',async()=>{
 for(const [status,reason] of [[401,'authentication'],[403,'administrator'],[404,'reverse proxy'],[302,'redirect']]){
  const result=await checkSourceApi({...args,fetchImpl:async()=>response(status)});
  assert.equal(result.ready,false);
  assert.match(result.reason,new RegExp(reason));
 }
});
test('source API smoke check rejects non-JSON HTML fallback and insecure URLs',async()=>{
 const result=await checkSourceApi({...args,fetchImpl:async()=>response(200,'text/html')});
 assert.equal(result.ready,false);
 assert.throws(()=>checkSourceApi({...args,baseUrl:'http://study.example'}),/HTTPS/);
});
