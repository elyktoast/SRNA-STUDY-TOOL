// Explicit one-question acceptance run. Never retry paid generation or publish.
import assert from 'node:assert/strict';
if (!process.argv.includes('--confirm-paid-generation')) throw Error('Explicit paid-generation confirmation required');
const project='https://xqyasyambwdyhsjkftqu.supabase.co';
const gateway='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const owner='c003287a-10ce-4cc9-926e-ef7c3a162a26';
const key=process.env.STAGING_SUPABASE_ANON_KEY;
assert.ok(key,'Staging anon key required');
let token=process.env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
const email=process.env.STAGING_TEST_ADMIN_EMAIL,password=process.env.STAGING_TEST_ADMIN_PASSWORD;
if(email&&password){
 const r=await fetch(project+'/auth/v1/token?grant_type=password',{method:'POST',redirect:'error',headers:{apikey:key,'Content-Type':'application/json'},body:JSON.stringify({email,password})});
 assert.equal(r.status,200,'Staging sign-in failed');
 token=(await r.json()).access_token;
}
assert.ok(token,'Staging administrator session required');
const identity=await fetch(project+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token},redirect:'error'});
assert.equal(identity.status,200,'Staging identity unavailable');
assert.equal((await identity.json()).id,owner,'Acceptance run must use the textbook owner account');
const headers={Origin:'https://staging.srnastudytool.com',Authorization:'Bearer '+token,'Content-Type':'application/json'};
async function call(path,body){
 const r=await fetch(gateway+path,{method:body?'POST':'GET',headers,redirect:'error',...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(240000)});
 const data=await r.json().catch(()=>null);
 if(!data)throw Error('Staging acceptance received a non-JSON response: HTTP '+r.status);
 if(!r.ok){
  // Only fixed machine-readable categories; never log provider output or evidence.
  const safe=v=>typeof v==='string'&&/^[A-Za-z0-9_]{1,80}$/.test(v)?v:'UNCLASSIFIED';
  console.log(JSON.stringify({path,status:r.status,error:safe(data.error),rule:safe(data.rule),failed_step:safe(data.failed_step)}));
  throw Error('Staging acceptance request failed: HTTP '+r.status);
 }
 return data;
}
// Keep earlier recovery failures visibly flagged; this is an automated defect
// report under the authenticated owner account, never human clinical approval.
for(const [id,reason] of [
 ['038defcb-295a-43a9-bdb4-5bb6a310b183','Text-only draft omitted its required item-level verification flag.'],
 ['11d8fe2a-af0c-4986-ab17-f1524eb2fe1a','The guarded rewrite omitted required option error_pattern tags; quality validation failed.'],
 ['273d8969-5957-4aec-9c4d-7c46548de822','Option evidence remained unsupported after the single rewrite; quality validation failed.'],
 ['eec2209c-419d-40ea-b830-6586d2b06125','Citation/quotation validation and guarded rewrite failed.'],
 ['d87e0523-a4bd-40a9-8f61-cdaabd6ad297','Another option is also source-supported; the primary/secondary ranking is unsupported.']
]){
 const previous=await call('/generation/drafts/'+id);
 if(['pending_review','needs_revision'].includes(previous.status)){
  const flagged=await call('/generation/drafts/'+id+'/review',{status:'needs_revision',notes:'Automated recovery QA: '+reason+' Kept unpublished; no human clinical approval performed.'});
  assert.equal(flagged.status,'needs_revision');assert.equal(flagged.published,false);
 }
}
const request={topic:'increased O2 consumption and decreased FRC',page_start:1280,page_end:1280,mode:'NCE',domain:'III',section:'H',objective:'III.H.4',format:'MC',item_id:crypto.randomUUID(),textbook_id:'6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d'};
const preflight=await call('/generation/preflight',request);
assert.equal(preflight.dry_run,true);assert.equal(preflight.can_publish,false);
assert.ok(preflight.passage_count>0,'No indexed evidence');
assert.equal(preflight.review_readiness?.blind_review,'configured');
assert.equal(preflight.review_readiness?.rewrite,'configured');
console.log('Indexed textbook evidence and independent review configuration verified');
const connection=await call('/generation/provider-check');
assert.equal(connection.container_relay,'OK');
assert.equal(connection.metadata_ready,true);
assert.ok(connection.providers.every(p=>p.provider!=='gemini'));
console.log('Signed container relay and active provider metadata verified');
const generated=await call('/generation/one',request);
assert.equal(generated.can_publish,false);assert.equal(generated.published,false);
assert.equal(generated.dry_run,false);assert.ok(generated.item);
assert.match(generated.draft_id,/^[a-f0-9-]{36}$/);
const saved=await call('/generation/drafts/'+generated.draft_id);
assert.equal(saved.draft_id,generated.draft_id);
assert.equal(saved.status,'pending_review');
const stages=Object.fromEntries(Object.entries(generated.screening?.stages||{}).map(([name,s])=>[name,s.status]));
console.log(JSON.stringify({draft_id:generated.draft_id,status:saved.status,published:false,stages,generator_issue_rules:(generated.generator_issues||[]).map(i=>i.rule_id),rewrite_attempts:generated.screening?.rewrite_attempts_used}));
assert.equal(stages.schema,'pass','Generated schema did not pass');
assert.equal(stages.deterministic_text,'pass','Deterministic wording screening did not pass');
assert.equal(stages.evidence,'pass','Evidence validation did not pass');
assert.equal(stages.blind_model,'pass','Independent blind review did not pass');
assert.equal((generated.generator_issues||[]).length,0,'Unresolved generator issues');
console.log('One authenticated textbook-grounded question persisted as an unpublished draft');
