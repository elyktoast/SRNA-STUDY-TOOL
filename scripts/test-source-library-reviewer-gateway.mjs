import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const source=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
const gateway=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).default;
const origin='https://staging.srnastudytool.com';
const base='https://gateway.example/review/manifest?path=owner%2Fbook.pdf';
const calls={auth:0,container:0};
const oldFetch=globalThis.fetch;
globalThis.fetch=async()=>{calls.auth++;return Response.json({id:'user-1',is_anonymous:false})};
const env={STAGING_ONLY:'true',SUPABASE_URL:'https://xqyasyambwdyhsjkftqu.supabase.co',SUPABASE_ANON_KEY:'test',
 REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>{calls.container++;return new Response('{"approval_enabled":false}',{headers:{'X-Review-Approval-Enabled':'false','Content-Type':'application/json','X-Verified-Source-SHA256':'a'.repeat(64)}})}})}};
const request=(url=base,{method='GET',headers={}}={})=>gateway.fetch(new Request(url,{method,headers:{Origin:origin,Authorization:'Bearer valid',...headers}}),env);
test('authenticated staging request forwards only read-only manifest',async()=>{
 const r=await request();assert.equal(r.status,200);assert.equal(r.headers.get('X-Review-Approval-Enabled'),'false');
 assert.equal(r.headers.get('Access-Control-Allow-Origin'),origin);
});
test('unsafe origin and approval routes are rejected before auth or container',async()=>{
 for(const [url,headers] of [[base,{Origin:'https://srnastudytool.com'}],['https://gateway.example/review/approve',{}]]){
  const before={...calls};const r=await request(url,{headers});assert.equal(r.status,403);
  assert.deepEqual(calls,before);
 }
});
test('strict preflight accepts only GET Authorization',async()=>{
 const r=await request(base,{method:'OPTIONS',headers:{'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'}});
 assert.equal(r.status,204);
 for(const headers of [{'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Authorization'},
 {'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization, X-Receipt'}]){
  assert.equal((await request(base,{method:'OPTIONS',headers})).status,403);
 }
});
test('invalid bearer token, extra query parameters, and disabled staging fail closed',async()=>{
 assert.equal((await request(base,{headers:{Authorization:'bad'}})).status,401);
 assert.equal((await request(base+'&approved=true')).status,400);
 assert.equal((await gateway.fetch(new Request(base,{headers:{Origin:origin,Authorization:'Bearer valid'}}),{...env,STAGING_ONLY:'false'})).status,503);
});
test('rejects upstream success without verified source digest',async()=>{
 const isolated={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>new Response('{}',{headers:{'X-Review-Approval-Enabled':'false','Content-Type':'application/json'}})})}};
 const r=await gateway.fetch(new Request(base,{headers:{Origin:origin,Authorization:'Bearer valid'}}),isolated);
 assert.equal(r.status,502);
});
test('rejects preview without PNG digest',async()=>{
 const r=await request('https://gateway.example/review/page.png?path=owner%2Fbook.pdf&page=1');
 assert.equal(r.status,502);
});
test.after(()=>{globalThis.fetch=oldFetch});
