import assert from 'node:assert/strict';
let token=process.env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
const key=process.env.STAGING_SUPABASE_ANON_KEY;
const pdf=process.env.SRNA_STAGING_REVIEWER_PDF_KEY;
const gateway='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const project='https://xqyasyambwdyhsjkftqu.supabase.co';
const origin='https://staging.srnastudytool.com';
function check(value,name){if(!value)throw Error(name+': missing secret or variable')}
for(const [v,n] of [[key,'staging anon key'],[pdf,'test PDF']])check(v,n);
const email=process.env.STAGING_TEST_ADMIN_EMAIL;
const password=process.env.STAGING_TEST_ADMIN_PASSWORD;
if(email||password){
 check(email,'admin email');
 check(password,'admin password');
 const response=await fetch(project+'/auth/v1/token?grant_type=password',{
  method:'POST',
  headers:{apikey:key,'Content-Type':'application/json'},
  body:JSON.stringify({email,password}),
  redirect:'error'
 });
 if(!response.ok)throw Error('Staging admin sign-in failed: HTTP '+response.status);
 const session=await response.json();
 if(typeof session.access_token!=='string')throw Error('Staging sign-in returned no access token');
 token=session.access_token;
 console.log('Fresh staging admin token acquired for diagnostic run');
}
check(token,'admin token');
function jwt(value){try{return JSON.parse(Buffer.from(value.split('.')[1],'base64url').toString('utf8'))}catch{return null}}
const a=jwt(key),t=jwt(token);
assert.equal(a?.role,'anon','legacy anon key role mismatch');
assert.equal(a?.ref,'xqyasyambwdyhsjkftqu','legacy anon key project mismatch');
assert.equal(t?.iss,project+'/auth/v1','admin token issuer mismatch');
assert.ok(t.exp>Math.floor(Date.now()/1000),'admin token expired');
console.log('STEP 1: staging credentials: valid structure and project');
// Staging-only automated verification can run on branch pushes before this workflow exists on main.
// Fetch the identity endpoint without logging any credential or server response.
const id=await fetch(project+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token},redirect:'manual'});
console.log('STEP 2: direct Supabase identity: HTTP',id.status);
assert.equal(id.status,200,'direct Supabase identity failed; stop before Container');
const user=await id.json();
assert.ok(user?.id&&!user.is_anonymous,'identity must be an authenticated user');
const headers={Origin:origin,Authorization:'Bearer '+token};
const negative=await fetch(gateway+'/review/manifest?path=invalid.pdf',{headers:{Origin:origin}});
console.log('STEP 3: unauthenticated gateway boundary: HTTP',negative.status);
assert.equal(negative.status,401);
const url=gateway+'/review/manifest?path='+encodeURIComponent(pdf);
// A newly deployed Container can briefly exit/restart during cold startup.
// Retry only that transient gateway response; never retry authentication,
// integrity failures, generation calls, or unexpected upstream errors.
let manifestResponse;
for(let attempt=1;attempt<=3;attempt++){
 manifestResponse=await fetch(url,{headers,redirect:'manual'});
 if(manifestResponse.status!==503||attempt===3)break;
 const transient=await manifestResponse.clone().json().catch(()=>null);
 if(transient?.error!=='reviewer_unavailable')break;
 console.log('STEP 4: reviewer container temporarily unavailable; bounded startup retry',attempt,'of 2');
 await new Promise(resolve=>setTimeout(resolve,5000));
}
let safeError='none';
if(manifestResponse.status!==200){
 const body=await manifestResponse.json().catch(()=>null);
 const allowed=new Set(['trusted_review_conflict','source_integrity_conflict','review_queue_conflict','review_queue_invalid','review_manifest_conflict','invalid_review_queue','invalid_source_attestation','source_changed','identity_unavailable','reviewer_unavailable','staging_not_configured','forbidden','unsafe_upstream','invalid_manifest','missing_source_integrity','manifest_integrity_mismatch','invalid_manifest_type','reviewer_backend_unavailable']);
 safeError=allowed.has(body?.error)?body.error:'unclassified';
 if(body?.error==='reviewer_backend_unavailable' && ['configuration','database','dependency','backend'].includes(body?.stage)) safeError+=':'+body.stage;
}
console.log('STEP 4: authenticated Container -> manifest: HTTP',manifestResponse.status,'category',safeError);
if(manifestResponse.status===409){
 const body=await manifestResponse.clone().json().catch(()=>null);
 const allowedRules=new Set(['ATTESTATION_MISMATCH','QUEUE_FINGERPRINT_MISMATCH','QUEUE_SOURCE_MISMATCH','QUEUE_PAGE_INVALID','SOURCE_CHANGED','MANIFEST_IDENTITY_MISMATCH','PAGE_OUT_OF_RANGE','PAGE_INTEGRITY_MISMATCH','SOURCE_MISSING','ATTESTATION_MISSING','QUEUE_MISSING','ATTESTATION_SIZE_INVALID','ATTESTATION_JSON_INVALID','QUEUE_SIZE_INVALID','QUEUE_JSON_INVALID','SOURCE_VERIFICATION_UNKNOWN']);
 console.log('STEP 4: conflict diagnostic: HTTP 409; safe error category',safeError,'rule',allowedRules.has(body?.rule)?body.rule:'UNCLASSIFIED');
}
assert.equal(manifestResponse.status,200,'Container/manifest failed: inspect staging_reviewer_failure substage in Cloudflare');
const manifest=await manifestResponse.json();
assert.match(manifest.source_sha256,/^[a-f0-9]{64}$/);
assert.ok(Number.isInteger(manifest.pdf_page_count)&&manifest.pdf_page_count>0);
console.log('STEP 5: manifest integrity: passed, page count',manifest.pdf_page_count);
let pageResponse;
for(let attempt=1;attempt<=3;attempt++){
 pageResponse=await fetch(gateway+'/review/page.png?path='+encodeURIComponent(pdf)+'&page=1',{headers,redirect:'manual'});
 if(pageResponse.status!==503||attempt===3)break;
 const failure=await pageResponse.clone().json().catch(()=>null);
 const category=['reviewer_unavailable','reviewer_backend_unavailable'].includes(failure?.error)?failure.error:'unclassified';
 console.log('STEP 6: first-page PNG transient HTTP 503, category',category,'attempt',attempt);
 if(category!=='reviewer_unavailable')break;
 await new Promise(resolve=>setTimeout(resolve,5000));
}
if(pageResponse.status!==200){
 const failure=await pageResponse.clone().json().catch(()=>null);
 const allowed=new Set(['reviewer_unavailable','reviewer_backend_unavailable','trusted_review_unavailable','staging_not_configured','identity_unavailable']);
 console.log('STEP 6: page retrieval failure category',allowed.has(failure?.error)?failure.error:'unclassified','HTTP',pageResponse.status);
}
console.log('STEP 6: first-page PNG: HTTP',pageResponse.status);
assert.equal(pageResponse.status,200);
assert.match(pageResponse.headers.get('Content-Type')||'',/^image\/png/i);
const bytes=new Uint8Array(await pageResponse.arrayBuffer());
assert.ok([137,80,78,71,13,10,26,10].every((b,i)=>bytes[i]===b),'PNG signature invalid');
const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
assert.equal(hash,pageResponse.headers.get('X-Page-Image-SHA256'),'PNG digest mismatch');
assert.equal(pageResponse.headers.get('X-Verified-Source-SHA256'),manifest.source_sha256,'PDF digest mismatch');
console.log('STEP 7: PDF and page SHA256 integrity: passed');

const preflightOptions=await fetch(gateway+'/generation/preflight',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'},redirect:'manual'});
console.log('STEP 8: generation CORS preflight: HTTP',preflightOptions.status);
assert.equal(preflightOptions.status,204,'generation CORS route unavailable');
const anonymousGeneration=await fetch(gateway+'/generation/preflight',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:'{}',redirect:'manual'});
console.log('STEP 9: unauthenticated generation boundary: HTTP',anonymousGeneration.status);
assert.equal(anonymousGeneration.status,401,'generation endpoint must reject anonymous callers');
const preflightRequest={method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({topic:'airway',mode:'NCE',domain:'I',section:'A',objective:'I.A.1',item_id:'preflight',format:'MC'}),redirect:'manual'};
let evidenceResponse;
for(let attempt=1;attempt<=3;attempt++){
 evidenceResponse=await fetch(gateway+'/generation/preflight',preflightRequest);
 if(evidenceResponse.status!==503||attempt===3)break;
 const transient=await evidenceResponse.clone().json().catch(()=>null);
 if(transient?.error!=='reviewer_unavailable')break;
 console.log('STEP 10: generation container temporarily unavailable; bounded startup retry',attempt,'of 2');
 await new Promise(resolve=>setTimeout(resolve,5000));
}
const evidence=await evidenceResponse.json().catch(()=>null);
const evidenceStatus=evidenceResponse.status===200?'indexed_evidence_found':evidenceResponse.status===422&&['no_indexed_evidence','generation_or_evidence_unavailable'].includes(evidence?.error)?'no_indexed_evidence':'unexpected_response';
const safeGenerationRules=new Set(['UPSTREAM_CONNECTION','UPSTREAM_HTTP','DEPENDENCY_UNAVAILABLE','RUNTIME_IO','GENERATION_RUNTIME_ERROR','PROVIDER_TRANSPORT','PROVIDER_RESPONSE','PROVIDER_AUTH','PROVIDER_FORBIDDEN','PROVIDER_RATE_LIMIT','PROVIDER_REQUEST_REJECTED','PROVIDER_UPSTREAM','PROVIDER_HTTP_OTHER','PROVIDER_TIMEOUT','PROVIDER_NETWORK','PROVIDER_INVALID_JSON','PROVIDER_REDIRECT','PROVIDER_ENDPOINT','PROVIDER_REQUEST','PROVIDER_REQUEST_SIZE','PROVIDER_RESPONSE_SIZE','DATABASE_CONNECTION','DATABASE_TIMEOUT','DATABASE_NETWORK','RELAY_AUTH','RELAY_UNAVAILABLE','RELAY_EDGE_403']);
const safeGenerationError=new Set(['generation_preflight_unavailable','generation_or_evidence_unavailable','reviewer_backend_unavailable','reviewer_unavailable','no_indexed_evidence']);
const diagnosticError=safeGenerationError.has(evidence?.error)?evidence.error:'unclassified';
const diagnosticRule=safeGenerationRules.has(evidence?.rule)?evidence.rule:'unclassified';
const diagnosticStage=['configuration','database','dependency','backend'].includes(evidence?.stage)?evidence.stage:'unclassified';
console.log('STEP 10: authenticated generation preflight: HTTP',evidenceResponse.status,'category',evidenceStatus,'error',diagnosticError,'rule',diagnosticRule,'stage',diagnosticStage);
assert.ok(evidenceStatus!=='unexpected_response','generation preflight failed or service unavailable');
if(evidenceResponse.status===200){
 assert.equal(evidence?.dry_run,true);
 assert.equal(evidence?.can_publish,false);
 assert.equal(evidence?.database_writes,false);
 assert.ok(Number.isSafeInteger(evidence?.passage_count)&&evidence.passage_count>0);
}

 // Provider readiness is a read-only GET to Groq's models endpoint, never generation.
 // Keep opt-in failures visible without turning an intentionally disabled provider into a deployment failure.
const providerResponse=await fetch(gateway+'/generation/provider-check',{method:'GET',headers,redirect:'manual'});
const providerBody=await providerResponse.json().catch(()=>null);
const providerRule=new Set(['OK','PROVIDER_AUTH','PROVIDER_FORBIDDEN','PROVIDER_RATE_LIMIT','PROVIDER_OTHER']).has(providerBody?.rule)?providerBody.rule:'UNCLASSIFIED';
const providerState=providerResponse.status===200?providerRule:providerResponse.status===403?'GENERATION_DISABLED':providerResponse.status===503?(['RELAY_EDGE_403','RELAY_NETWORK','RELAY_HTTP_400','RELAY_HTTP_401','RELAY_HTTP_403','RELAY_HTTP_404','RELAY_HTTP_502','RELAY_HTTP_503'].includes(providerBody?.rule)?providerBody.rule:'PROVIDER_CHECK_UNAVAILABLE'):'UNEXPECTED';
console.log('STEP 11: read-only provider check: HTTP',providerResponse.status,'state',providerState);
if(providerBody?.check==='hybrid_provider_readiness'){
 assert.equal(providerBody.generation_performed,false);
 assert.equal(providerBody.providers?.length,2);
 assert.equal(typeof providerBody.metadata_ready,'boolean','metadata readiness must be explicit');
 assert.equal(providerBody.generation_ready,false,'metadata probes cannot certify inference readiness');
 const providerNames=new Set();
 for(const p of providerBody.providers){
  assert.equal(p.generation_performed,false);
  assert.equal(typeof p.provider,'string');
  assert.equal(typeof p.state,'string');
  assert.ok(p.state.length>0,'provider state must be explicit');
  providerNames.add(p.provider.toLowerCase());
  console.log('STEP 11 provider:',p.provider,'state',p.state);
 }
 assert.equal(providerNames.size,2,'provider check must report two distinct active providers');
 assert.ok([...providerNames].some(name=>name.includes('groq')),'Groq provider missing');
 assert.ok(!providerNames.has('gemini'),'Gemini must remain disabled');
 assert.ok([...providerNames].some(name=>name.includes('cloudflare')),'Cloudflare AI provider missing');
}
assert.ok([200,403,503].includes(providerResponse.status),'unexpected provider-check HTTP status');
if(providerResponse.status===200){
 assert.equal(providerBody?.generation_performed,false,'provider-check must never generate');
 assert.ok(['groq_models','groq_models_via_signed_relay','hybrid_provider_readiness'].includes(providerBody?.check));
 if(['groq_models','groq_models_via_signed_relay'].includes(providerBody.check))assert.ok([200,401,403,429,0].includes(providerBody?.provider_status));
 if(providerBody.check==='groq_models_via_signed_relay'){
  assert.ok([200,401,403,429,0].includes(providerBody?.worker_status));
  assert.ok(['OK','UNAVAILABLE'].includes(providerBody?.container_relay));
  assert.equal(typeof providerBody?.generation_ready,'boolean');
  if(providerBody.generation_ready){assert.equal(providerBody.provider_status,200);assert.equal(providerBody.worker_status,200);assert.equal(providerBody.container_relay,'OK');}
 }
}
const draftResponse=await fetch(gateway+'/generation/drafts',{method:'GET',headers,redirect:'manual'});
const draftBody=await draftResponse.json().catch(()=>null);
console.log('STEP 12: private draft-bank read: HTTP',draftResponse.status,'shape',Array.isArray(draftBody?.drafts)?'draft_list':'unavailable');
assert.equal(draftResponse.status,200,'private draft-bank read unavailable');
assert.ok(Array.isArray(draftBody?.drafts),'draft bank must return a private draft list');
assert.ok(draftBody.drafts.every(d=>d?.published!==true),'draft listing must not contain published items');
