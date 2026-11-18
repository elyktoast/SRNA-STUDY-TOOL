import assert from 'node:assert/strict';
import {test} from 'node:test';
import {EventEmitter} from 'node:events';
import {stagingFetch} from './staging-http-request.mjs';
const url='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/generation/one';
function transport({status=200,chunks=['{"ok":true}'],delay=0}={}){
 let count=0;const impl=(_url,options,callback)=>{
  count++;if(options.method==='POST')assert.equal(options.headers['Content-Length'],'2');assert.ok(options.headers['User-Agent']);const req=new EventEmitter();req.write=()=>{};
  req.destroy=error=>req.emit('error',error);
  req.end=()=>setTimeout(()=>{
   if(options.signal.aborted){req.emit('error',Error('Aborted'));return;}
   const res=new EventEmitter();res.statusCode=status;res.headers={'content-type':'application/json'};callback(res);
   for(const chunk of chunks)res.emit('data',Buffer.from(chunk));res.emit('end');
  },delay);
  return req;
 };return {impl,count:()=>count};
}
test('one HTTPS request accepts delayed headers within the explicit signal and parses JSON',async()=>{
 const f=transport({delay:20});const response=await stagingFetch(url,{method:'POST',body:'{}',signal:AbortSignal.timeout(1000)},f.impl);
 assert.deepEqual(await response.json(),{ok:true});assert.equal(f.count(),1);
});
test('redirects, interrupted deadlines and oversized responses never retry',async()=>{
 for(const args of [{status:302},{chunks:['x'.repeat(4194305)]},{delay:20}]){
  const f=transport(args);await assert.rejects(stagingFetch(url,{signal:AbortSignal.timeout(args.delay?1:1000)},f.impl));assert.equal(f.count(),1);
 }
});
test('HTTPS destination and method checks happen before network or credentials are sent',()=>{
 const f=transport();for(const bad of ['http://api.github.com','https://example.com','https://api.github.com:444','https://user@api.github.com'])assert.throws(()=>stagingFetch(bad,{},f.impl));
 assert.throws(()=>stagingFetch(url,{method:'DELETE'},f.impl));assert.equal(f.count(),0);
});
