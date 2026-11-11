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
test('draft review rejects upstream publication and does not require PDF source headers',async()=>{
 const endpoint=draftListUrl+'/'+draftId+'/review';
 const makeRequest=()=>new Request(endpoint,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:JSON.stringify({status:'approved'})});
 const approved={...draftEnv,REVIEWER_CONTAINER:{getByName:()=>({
  startAndWaitForPorts:async()=>{},
  fetch:async()=>Response.json({draft_id:draftId,published:false,status:'approved'})
 })}};
 const accepted=await gateway.fetch(makeRequest(),approved);
 assert.equal(accepted.status,200);
 assert.equal((await accepted.json()).published,false);
 const unsafe={...approved,REVIEWER_CONTAINER:{getByName:()=>({
  startAndWaitForPorts:async()=>{},
  fetch:async()=>Response.json({draft_id:draftId,published:true,status:'approved'})
 })}};
 assert.equal((await gateway.fetch(makeRequest(),unsafe)).status,502);
});
test('draft review rejects missing authorization, invalid origin, and oversize payload',async()=>{
 const endpoint=draftListUrl+'/'+draftId+'/review';
 const makeRequest=(headers,body='{}')=>new Request(endpoint,{method:'POST',headers:{'Content-Type':'application/json',...headers},body});
 assert.equal((await gateway.fetch(makeRequest({Origin:origin}),draftEnv)).status,401);
 assert.equal((await gateway.fetch(makeRequest({Origin:'https://srnastudytool.com',Authorization:'Bearer valid'}),draftEnv)).status,403);
 assert.equal((await gateway.fetch(makeRequest({Origin:origin,Authorization:'Bearer valid'},'x'.repeat(8193)),draftEnv)).status,413);
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

test('saved draft revalidation route is allowed as read-only GET only',async()=>{
 const url='https://gateway.example/generation/drafts/abc90a93-41f8-4d7c-8e27-94a609135572/revalidate';
 const before=calls.container;
 const result=await request(url);
 assert.notEqual(result.status,403,'gateway must recognize revalidation route');
 assert.notEqual(result.status,405,'gateway must allow GET revalidation');
 assert.ok(calls.container>before,'request should reach reviewer container');
 const post=await request(url,{method:'POST',headers:{'Content-Type':'application/json'}});
 assert.equal(post.status,405);
 const opt=await request(url,{method:'OPTIONS',headers:{'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'}});
 assert.equal(opt.status,204);
});

test('revision routes permit authenticated GET and guarded POST only',async()=>{
 const id='abc90a93-41f8-4d7c-8e27-94a609135572';
 const path='https://gateway.example/generation/drafts/'+id+'/revisions';
 const draftEnv={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>Response.json({draft_id:id,published:false,revisions:[],current_question:{stem:'Test'}})})}};
 const draftRequest=(method,body)=>gateway.fetch(new Request(path,{method,headers:{Origin:origin,Authorization:'Bearer valid',...(body?{'Content-Type':'application/json'}:{})},...(body?{body:JSON.stringify(body)}:{})}),draftEnv);
 const get=await draftRequest('GET');
 assert.equal(get.status,200);
 const options=await request(path,{method:'OPTIONS',headers:{
  'Access-Control-Request-Method':'POST',
  'Access-Control-Request-Headers':'Authorization, Content-Type'}});
 assert.equal(options.status,204);
 assert.match(options.headers.get('Access-Control-Allow-Methods'),/POST/);
 const posted=await draftRequest('POST',{expected_parent_sha256:'a'.repeat(64),citation_excerpts:{},option_evidence:{},reviewer_notes:'Verified'});
 assert.equal(posted.status,200);
 assert.equal((await request(path,{method:'DELETE'})).status,405);
 assert.equal((await request(path+'?unsafe=true')).status,400);
 assert.equal((await request(path,{method:'POST',headers:{'Content-Type':'text/plain'}})).status,400);
 assert.equal((await request(path,{method:'POST',headers:{Origin:'https://srnastudytool.com','Content-Type':'application/json'}})).status,403);
});

test('authenticated indexed textbook catalog accepts JSON without PDF attestation headers',async()=>{
 const books=[{id:'6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d',title:'Indexed book'}];
 const isolated={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async req=>{
  assert.equal(new URL(req.url).pathname,'/generation/textbooks');
  assert.equal(req.method,'GET');
  return Response.json({textbooks:books});
 }})}};
 const url='https://gateway.example/generation/textbooks';
 const response=await gateway.fetch(new Request(url,{headers:{Origin:origin,Authorization:'Bearer valid'}}),isolated);
 assert.equal(response.status,200);
 assert.deepEqual(await response.json(),{textbooks:books});
 assert.equal((await gateway.fetch(new Request(url+'?path=other',{headers:{Origin:origin,Authorization:'Bearer valid'}}),isolated)).status,400);
 assert.equal((await gateway.fetch(new Request(url,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid'}}),isolated)).status,405);
});
test('PDF review routes still require attestation header and source digest',async()=>{
 const isolated={...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>Response.json({source_sha256:'a'.repeat(64),pdf_page_count:2,approval_enabled:false})})}};
 const response=await gateway.fetch(new Request(base,{headers:{Origin:origin,Authorization:'Bearer valid'}}),isolated);
 assert.equal(response.status,502);
 assert.equal((await response.json()).error,'unsafe_upstream');
});

test('authenticated checkpoint readiness uses its exact read-only JSON contract without PDF headers',async()=>{
 const url='https://gateway.example/generation/checkpoint-readiness';
 const valid={ready:true,check:'checkpoint_database_readiness',generation_performed:false,database_writes:false};
 const isolated=value=>({...env,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async req=>{
  assert.equal(req.method,'GET');
  return Response.json(value);
 }})}});
 const req=()=>new Request(url,{headers:{Origin:origin,Authorization:'Bearer valid'}});
 const response=await gateway.fetch(req(),isolated(valid));
 assert.equal(response.status,200);
 assert.deepEqual(await response.json(),valid);
 for(const change of [{ready:false},{check:'other'},{generation_performed:true},{database_writes:true},{extra:'private'}]){
  const rejected=await gateway.fetch(req(),isolated({...valid,...change}));
  assert.equal(rejected.status,502);
  assert.equal((await rejected.json()).error,'unsafe_checkpoint_response');
 }
 assert.equal((await gateway.fetch(new Request(url,{headers:{Origin:origin}}),isolated(valid))).status,401);
 assert.equal((await gateway.fetch(new Request(url,{headers:{Origin:'https://srnastudytool.com',Authorization:'Bearer valid'}}),isolated(valid))).status,403);
});

test('Cloudflare delivery metadata reaches the container without its provider credential',async()=>{
 const target={...generationEnv,AI_GENERATION_OPT_IN:'true',AI_PROVIDER_ENDPOINT:'https://api.groq.com/openai/v1/chat/completions',
  AI_ALLOWED_HOSTS:'api.groq.com',AI_PROVIDER_API_KEY:'groq-secret',AI_GENERATOR_MODEL:'openai/gpt-oss-120b',
  AI_AUTHORING_PROVIDER:'cloudflare',AI_CLOUDFLARE_MODEL:'@cf/openai/gpt-oss-120b',AI_CLOUDFLARE_API_TOKEN:'cf-private'};
 let observed;
 target.REVIEWER_CONTAINER={getByName:()=>({startAndWaitForPorts:async options=>{observed=options.startOptions.envVars;},
  fetch:async()=>Response.json({passage_count:2,dry_run:true,can_publish:false,database_writes:false})})};
 const response=await gateway.fetch(new Request(generationUrl,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'{}'}),target);
 assert.equal(response.status,200);
 assert.equal(observed.AI_AUTHORING_PROVIDER,'cloudflare');assert.equal(observed.AI_CLOUDFLARE_MODEL,'@cf/openai/gpt-oss-120b');
 assert.ok(!Object.hasOwn(observed,'AI_CLOUDFLARE_API_TOKEN'));
});


test('lecture planning forwards authenticated POST to private reviewer without generation',async()=>{
 const endpoint='https://gateway.example/generation/lecture-plan';
 let forwarded=false;
 const safe={...generationEnv,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async req=>{
  forwarded=true;
  assert.equal(req.method,'POST');
  assert.equal(new URL(req.url).pathname,'/generation/lecture-plan');
  const body=await req.json();
  assert.equal(body.lecture_text,'Airway management objectives');
  return Response.json({jobs:[],count:0,auto_generate:false,auto_publish:false,database_writes:false,paid_calls_requested:false});
 }})}};
 const res=await gateway.fetch(new Request(endpoint,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:JSON.stringify({lecture_text:'Airway management objectives',textbook_id:'book-1'})}),safe);
 assert.equal(res.status,200);
 assert.equal((await res.json()).auto_generate,false);
 assert.equal(forwarded,true);
});
test('lecture planning enforces POST CORS and 16KiB limit',async()=>{
 const endpoint='https://gateway.example/generation/lecture-plan';
 const options=await request(endpoint,{method:'OPTIONS',headers:{'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Content-Type, Authorization'}});
 assert.equal(options.status,204);
 const get=await request(endpoint,{method:'GET'});
 assert.equal(get.status,405);
 const before=calls.container;
 const oversized=await gateway.fetch(new Request(endpoint,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'x'.repeat(16385)}),generationEnv);
 assert.equal(oversized.status,413);
 assert.equal(calls.container,before);
});

test('lecture planning rejects upstream generation or publishing claims',async()=>{
 const endpoint='https://gateway.example/generation/lecture-plan';
 const unsafe={...generationEnv,REVIEWER_CONTAINER:{getByName:()=>({startAndWaitForPorts:async()=>{},fetch:async()=>Response.json({jobs:[{path:'/generation/one',body:{execute:true}}],count:1,auto_generate:true,auto_publish:false,database_writes:false})})}};
 const res=await gateway.fetch(new Request(endpoint,{method:'POST',headers:{Origin:origin,Authorization:'Bearer valid','Content-Type':'application/json'},body:'{}'}),unsafe);
 assert.equal(res.status,502);
 assert.equal((await res.json()).error,'unsafe_lecture_plan');
});

test('lecture planning rejects unauthenticated requests before contacting reviewer',async()=>{
 const endpoint='https://gateway.example/generation/lecture-plan';
 const before=calls.container;
 const res=await gateway.fetch(new Request(endpoint,{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:'{}'}),generationEnv);
 assert.equal(res.status,401);
 assert.equal(calls.container,before);
});

test('lecture panel is mounted in the AI create workspace, not after a detached node',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/create\.append\(evidencePanel,lecturePanel\)/);
 assert.doesNotMatch(ui,/evidencePanel\.after\(lecturePanel\)/);
 assert.match(ui,/storage\.planLectureQuestions\(/);
});

test('lecture planning UI offers optional user-selected blueprint without requiring domain codes',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/id="sl-lecture-use-objective"/);
 assert.match(ui,/const blueprint=useObjective\?/);
 assert.match(ui,/const options=\{textbook_id,count,mode,format,\.\.\.blueprint\}/);
 assert.match(ui,/otherwise suggest automatically/);
});

test('staging question bank uses existing authenticated review contract and remains unpublished',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 const storage=readFileSync(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url),'utf8');
 assert.match(ui,/Approved Question Bank \(staging only\)/);
 assert.match(ui,/renderDraftCollection\('bank'\)/);
 assert.match(ui,/storage\.reviewGeneratedDraft\(draft\.draft_id,'approved_for_bank',notes\)/);
 assert.match(ui,/storage\.reviewGeneratedDraft\(draft\.draft_id,'rejected','Rejected by admin'\)/);
 assert.match(storage,/generationRequest\('\/generation\/drafts\/'\+draftId\+'\/review'/);
 assert.match(ui,/result\.published!==false/);
});

test('staging approval UI blocks unresolved current-index validation issues',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/if\(checked\.issues\.length\)throw Error/);
 assert.match(ui,/unresolved validation issue\(s\)/);
});

test('AI workspace has a dedicated approved bank tab sharing the draft collection view',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/data-sl-ai-view="bank" aria-pressed="false">Approved bank/);
 assert.match(ui,/view==='bank'\|\|view==='drafts'/);
 assert.match(ui,/renderDraftCollection\(view\)/);
});

test('lecture PDF/PPTX uploader uses authenticated bounded file-plan route',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 const storage=readFileSync(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url),'utf8');
 const gateway=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
 assert.match(ui,/id="sl-lecture-file" accept="\.pdf,\.pptx/);
 assert.match(ui,/storage\.planLectureFile\(lectureFile,options\)/);
 assert.match(storage,/generationRequest\('\/generation\/lecture-file-plan'/);
 assert.match(gateway,/const lectureFile=url\.pathname==='\/generation\/lecture-file-plan'/);
 assert.match(gateway,/lectureFile\?36\*1024\*1024/);
});

test('lecture PDF preview stays local and invalidates old object URLs',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/URL\.createObjectURL\(file\)/);
 assert.match(ui,/URL\.revokeObjectURL\(lecturePreviewUrl\)/);
 assert.match(ui,/Local PDF lecture preview/);
 assert.match(ui,/lectureInput\.addEventListener\('change'/);
});

test('file plan responses must pass fail-closed gateway schema validation',()=>{
 const gateway=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
 assert.match(gateway,/if\(upstream\.ok&&lectureFile\)/);
 assert.match(gateway,/unsafe_lecture_file_plan/);
 assert.match(gateway,/data\.paid_calls_requested!==false/);
 assert.match(gateway,/extraction\.requires_visual_review!==true/);
});

test('lecture file upload body is not rejected as a forbidden GET payload',()=>{
 const gateway=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
 assert.match(gateway,/!generation&&!generateOne&&!lecturePlan&&!lectureFile&&!draftWrite&&request\.headers\.get\('Content-Length'\)/);
 assert.match(gateway,/lectureFile\?36\*1024\*1024/);
});

test('lecture job evidence check uses read-only preflight, never generation',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/check\.textContent='Check indexed evidence'/);
 assert.match(ui,/storage\.generationPreflight\(job\.body\)/);
 assert.match(ui,/preflight\.dry_run!==true\|\|preflight\.can_publish!==false\|\|preflight\.database_writes!==false/);
});

test('lecture evidence handoff retains explicit paid-generation confirmation',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/transfer\.textContent='Use this lecture topic in AI Question Studio'/);
 assert.match(ui,/checkedEvidence=\{topic:body\.topic,mode:body\.mode,format:body\.format,/);
 assert.match(ui,/if\(!confirm\('Generate one staging AI question\?/);
 assert.match(ui,/storage\.generateOne\(request,/);
});

test('lecture transfer rejects missing exam blueprint classification',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/Lecture question classification is incomplete/);
 assert.match(ui,/body\.objective\.startsWith\(body\.domain\+'\.'\+body\.section\+'\.'\)/);
});

test('lecture blueprint objective pattern accepts real NCE objective IDs',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 const pattern=ui.match(/!\/(\^\(I\|II\|III\|IV\).*?\$)\/\.test\(body\.objective\)/);
 assert.ok(pattern,'lecture objective validator must exist');
 const validator=new RegExp(pattern[1]);
 assert.equal(validator.test('II.A.3'),true);
 assert.equal(validator.test('IV.C.12.1'),true);
 assert.equal(validator.test('II.A'),false);
 assert.equal(validator.test('II/A/3'),false);
});

test('lecture planning reports skipped blank pages and rejects malformed preflight counts',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/file_extraction\?\.skipped_blank_pages/);
 assert.match(ui,/Blank pages\/slides skipped:/);
 assert.match(ui,/!Number\.isSafeInteger\(preflight\.passage_count\)\|\|preflight\.passage_count<0/);
});


test('lecture planning accepts manually entered indexed textbook ID',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/const textbook_id=genEl\('sl-gen-book-select'\)\?\.value\|\|genEl\('sl-gen-book'\)\?\.value\.trim\(\)\|\|researchBookSelect\.value/);
});


test('generated question auto-saves unpublished draft and preserves manual retry',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/const saved=await storage\.saveGeneratedDraft\(result\.save_payload\)/);
 assert.match(ui,/result\.draft_id=saved\.draft_id/);
 assert.match(ui,/Use Save unpublished draft to retry/);
 assert.match(ui,/generatedForReview\.result\.draft_id=result\.draft_id/);
 assert.match(ui,/genEl\('sl-save-generated'\)\.disabled=!!result\.draft_id\|\|!result\.save_payload/);
});


test('lecture uploads allow 25 MiB files with base64 transport headroom',()=>{
 const adapter=readFileSync(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url),'utf8');
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 const gateway=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
 assert.match(adapter,/file\.size>25\*1024\*1024/);
 assert.match(ui,/max 25 MB/);
 assert.match(gateway,/lectureFile\?36\*1024\*1024/);
});


test('bulk draft review requires confirmation and per-draft validation; removal preserves audit history',()=>{
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 assert.match(ui,/Select all reviewable drafts/);
 assert.match(ui,/Approve selected to bank/);
 assert.match(ui,/Remove selected/);
 assert.match(ui,/await storage\.revalidateGeneratedDraft\(id\)/);
 assert.match(ui,/await storage\.reviewGeneratedDraft\(id,status,notes\)/);
 assert.match(ui,/Records remain in audit history/);
 assert.match(ui,/response\.status!==status\|\|response\.published!==false/);
});


test('staging admin initializes source workspace config without enabling production',()=>{
 const ui=readFileSync(new URL('../equipment/assets/admin-panel.js',import.meta.url),'utf8');
 assert.match(ui,/if\(location\.hostname!=='staging\.srnastudytool\.com'\)throw Error\('Staging source workspace is disabled on this page\.'\)/);
 assert.match(ui,/if\(!window\.MBU_SOURCE_LIBRARY_STAGING\)window\.MBU_SOURCE_LIBRARY_STAGING=Object\.freeze\(\{enabled:true,apiUrl:'https:\/\/source-library-staging\.srnastudytool\.com'\}\)/);
 assert.match(ui,/if\(!window\.MBU_SOURCE_LIBRARY_STAGING\.enabled\)throw Error\('Staging source workspace is disabled by configuration\.'\)/);
});


test('lecture file planning bypasses manifest-only upstream approval header guard',()=>{
 const gateway=readFileSync(new URL('../workers/source-library-staging/reviewer-gateway/src/index.js',import.meta.url),'utf8');
 assert.match(gateway,/!generation&&!generateOne&&!lecturePlan&&!lectureFile&&!draftRead&&!draftWrite&&!providerCheck&&!checkpointCheck&&!textbookList&&upstream\.headers\.get\('X-Review-Approval-Enabled'\)!=='false'/);
});
