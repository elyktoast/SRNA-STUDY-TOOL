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
const env={STAGING_DATABASE_URL:'postgresql://postgres:example@db.xqyasyambwdyhsjkftqu.supabase.co:5432/postgres',STAGING_R2_ACCOUNT_ID:'test-account',STAGING_R2_ACCESS_KEY_ID:'test-access',STAGING_R2_SECRET_ACCESS_KEY:'test-secret',STAGING_RECEIPT_SIGNING_SECRET:'test-signing-secret-placeholder-not-real',STAGING_ONLY:'true',SUPABASE_URL:'https://xqyasyambwdyhsjkftqu.supabase.co',SUPABASE_ANON_KEY:'test',
 REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>{calls.container++;return new Response('{"approval_enabled":false,"source_sha256":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","pdf_page_count":2}',{headers:{'X-Review-Approval-Enabled':'false','Content-Type':'application/json','X-Verified-Source-SHA256':'a'.repeat(64)}})}})}};
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
test('rejects manifest whose body does not match attested header',async()=>{
 const wrong={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>new Response(JSON.stringify({source_sha256:'b'.repeat(64),pdf_page_count:2,approval_enabled:false}),{headers:{'X-Review-Approval-Enabled':'false','Content-Type':'application/json','X-Verified-Source-SHA256':'a'.repeat(64)}})})}};
 const r=await gateway.fetch(new Request(base,{headers:{Origin:origin,Authorization:'Bearer valid'}}),wrong);
 assert.equal(r.status,502);
});
test('rejects manifest that enables approvals despite safe response header',async()=>{
 const unsafe={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>new Response(JSON.stringify({source_sha256:'a'.repeat(64),pdf_page_count:2,approval_enabled:true}),{headers:{'X-Review-Approval-Enabled':'false','Content-Type':'application/json','X-Verified-Source-SHA256':'a'.repeat(64)}})})}};
 const r=await gateway.fetch(new Request(base,{headers:{Origin:origin,Authorization:'Bearer valid'}}),unsafe);
 assert.equal(r.status,502);
});
const generationUrl='https://gateway.example/generation/preflight';
const generationEnv={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async req=>{
 calls.container++;
 assert.equal(req.method,'POST');
 assert.equal(req.headers.get('Content-Type'),'application/json');
 return Response.json({topic:'airway',passage_count:3,dry_run:true,can_publish:false,database_writes:false});
}})}};
test('generation preflight accepts authenticated bounded JSON and never publishes',async()=>{
 const res=await gateway.fetch(new Request(generationUrl,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:JSON.stringify({topic:'airway'})}),generationEnv);
 assert.equal(res.status,200);assert.equal((await res.json()).passage_count,3);
});
test('generation preflight OPTIONS requires POST and both headers',async()=>{
 const good=await request(generationUrl,{method:'OPTIONS',headers:{'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type, Authorization'}});
 assert.equal(good.status,204);
 assert.equal(good.headers.get('Access-Control-Allow-Methods'),'POST');
 const bad=await request(generationUrl,{method:'OPTIONS',headers:{'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'}});
 assert.equal(bad.status,403);
});
test('generation preflight rejects oversize body before container',async()=>{
 const before=calls.container;
 const res=await gateway.fetch(new Request(generationUrl,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'x'.repeat(8193)}),generationEnv);
 assert.equal(res.status,413);assert.equal(calls.container,before);
});
test('generation preflight rejects unsafe successful upstream responses',async()=>{
 const unsafe={...generationEnv,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>Response.json({passage_count:3,dry_run:false,can_publish:false,database_writes:false})})}};
 const res=await gateway.fetch(new Request(generationUrl,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'{}'}),unsafe);
 assert.equal(res.status,502);
});
test('single-question generation forwards only authenticated staging POST and rejects unsafe results',async()=>{
 const endpoint='https://gateway.example/generation/one';
 const generated={dry_run:false,can_publish:false,database_writes:false,requires_human_review:true,item:{stem:'Sample question'}};
 const safe={...generationEnv,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async req=>{
  assert.equal(req.method,'POST');return Response.json(generated);
 }})}};
 const request=()=>new Request(endpoint,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'{}'});
 const res=await gateway.fetch(request(),safe);
 assert.equal(res.status,200);assert.equal((await res.json()).item.stem,'Sample question');
 const unsafe={...safe,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>Response.json({...generated,can_publish:true})})}};
 assert.equal((await gateway.fetch(request(),unsafe)).status,502);
});
const draftListUrl='https://gateway.example/generation/drafts';
const draftId='00000000-0000-4000-8000-000000000002';
const draftEnv={...env,REVIEWER_CONTAINER:{getByName:()=>({
 startAndWaitForPorts:async()=>{},
 fetch:async req=>{
  if(req.method==='POST'&&req.url.endsWith('/generation/drafts'))return Response.json({draft_id:draftId,published:false,status:'pending_review'},{status:201});
  if(req.method==='POST'&&req.url.endsWith('/review'))return Response.json({draft_id:draftId,published:false,status:'approved'});
  assert.equal(req.method,'GET');
  if(req.url.endsWith('/generation/drafts'))return Response.json({drafts:[]});
  return Response.json({draft_id:draftId,published:false,status:'pending_review'});
 }
})}};
test('staging basket lists and saves private drafts and forwards authenticated review',async()=>{
 const list=await gateway.fetch(new Request(draftListUrl,{headers:{Origin:origin,Authorization:'Bearer valid'}}),draftEnv);
 assert.equal(list.status,200);assert.deepEqual((await list.json()).drafts,[]);
 const detail=await gateway.fetch(new Request(draftListUrl+'/'+draftId,{headers:{Origin:origin,Authorization:'Bearer valid'}}),draftEnv);
 assert.equal(detail.status,200);assert.equal((await detail.json()).published,false);
 const saved=await gateway.fetch(new Request(draftListUrl,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'{}'}),draftEnv);
 assert.equal(saved.status,201);assert.equal((await saved.json()).draft_id,draftId);
 const preflight=await gateway.fetch(new Request(draftListUrl,{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'}}),draftEnv);
 assert.equal(preflight.status,204);
 const review=await gateway.fetch(new Request(draftListUrl+'/'+draftId+'/review',{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'{}'}),draftEnv);
 assert.equal(review.status,200);assert.equal((await review.json()).status,'approved');
 const reviewPreflight=await gateway.fetch(new Request(draftListUrl+'/'+draftId+'/review',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'}}),draftEnv);
 assert.equal(reviewPreflight.status,204);
 const badReview=await gateway.fetch(new Request(draftListUrl+'/'+draftId+'/review',{method:'GET',headers:{Origin:origin,Authorization:'Bearer valid'}}),draftEnv);
 assert.equal(badReview.status,405);
});
test.after(()=>{globalThis.fetch=oldFetch});

test('checkpoint feature flag reaches the private container only with complete AI configuration',async()=>{
 const endpoint='https://gateway.example/generation/preflight';
 const flags=[];
 const baseAI={...generationEnv,AI_GENERATION_OPT_IN:'true',
  AI_GENERATION_CHECKPOINTS_ENABLED:'true',
  AI_PROVIDER_ENDPOINT:'https://api.groq.com/openai/v1/chat/completions',
  AI_ALLOWED_HOSTS:'api.groq.com',AI_PROVIDER_API_KEY:'test-provider-key',
  AI_GENERATOR_MODEL:'test-model',
  REVIEWER_CONTAINER:{getByName:()=>({
   startAndWaitForPorts:async ({startOptions})=>{flags.push(startOptions.envVars);},
   fetch:async()=>Response.json({dry_run:true,can_publish:false,database_writes:false,passage_count:2})
  })}};
 const makeRequest=()=>new Request(endpoint,{method:'POST',
  headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},
  body:'{}'});
 const ok=await gateway.fetch(makeRequest(),baseAI);
 assert.equal(ok.status,200);
 assert.equal(flags.length,1);
 assert.equal(flags[0].AI_GENERATION_CHECKPOINTS_ENABLED,'true');
 assert.equal(flags[0].AI_GENERATION_OPT_IN,'true');
 assert.equal(flags[0].AI_PROVIDER_API_KEY,'test-provider-key');
 const missing={...baseAI,AI_PROVIDER_API_KEY:''};
 const denied=await gateway.fetch(makeRequest(),missing);
 assert.equal(denied.status,503);
 assert.equal(flags.length,1,'must reject before starting private container');
 const disabled={...baseAI,AI_GENERATION_CHECKPOINTS_ENABLED:'false'};
 const off=await gateway.fetch(makeRequest(),disabled);
 assert.equal(off.status,200);
 assert.equal(flags.length,2);
 assert.equal(flags[1].AI_GENERATION_CHECKPOINTS_ENABLED,undefined);
});
