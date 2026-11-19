// Explicit one-question acceptance run. Never retry paid generation or publish.
import assert from 'node:assert/strict';
import {stagingFetch as fetch} from './staging-http-request.mjs';
import {stagingReadOnlyRetry} from './staging-read-only-retry.mjs';
import {isGenerationDisconnect,recoverCompletedGeneration} from '../equipment/assets/generation-completion-recovery.js';
const paid=process.argv.includes('--confirm-paid-generation');
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
 return stagingReadOnlyRetry(path,()=>callOnce(path,body));
}
async function callOnce(path,body){
 const r=await fetch(gateway+path,{method:body?'POST':'GET',headers,redirect:'error',...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(path==='/generation/one'?480000:240000)});
 const data=await r.json().catch(()=>null);
 if(!data){const error=Error('Staging acceptance received a non-JSON response: HTTP '+r.status);error.status=r.status;throw error;}
 if(!r.ok){
  // Only fixed machine-readable categories; never log provider output or evidence.
  const safe=v=>typeof v==='string'&&/^[A-Za-z0-9_]{1,80}$/.test(v)?v:'UNCLASSIFIED';
  console.log(JSON.stringify({path,status:r.status,error:safe(data.error),rule:safe(data.rule),failed_step:safe(data.failed_step),validation_detail:safe(data.validation_detail),validation_contract:typeof data.validation_contract==='string'&&/^2026-11-(10|11)-v[0-9]{1,2}$/.test(data.validation_contract)?data.validation_contract:'UNCLASSIFIED'}));
  const error=Error('Staging acceptance request failed: HTTP '+r.status);error.status=r.status;error.rule=data.rule;throw error;
 }
 return data;
}
const format=process.env.SRNA_STAGING_ACCEPTANCE_FORMAT||'MC';
assert.ok(['MC','MS','SA','DD','HS'].includes(format));
const topic=process.env.SRNA_STAGING_ACCEPTANCE_TOPIC||'Local anesthetic pharmacology';
const objective=process.env.SRNA_STAGING_ACCEPTANCE_OBJECTIVE||'I.C.5';
const textbook_id=process.env.SRNA_STAGING_ACCEPTANCE_TEXTBOOK||'62f162fd-6c12-4899-b45b-6466e688f570';
assert.ok(typeof topic==='string'&&topic.trim()&&topic.length<=500);
assert.match(objective,/^(I|II|III|IV)\.[A-Z]\.\d+(?:\.\d+)*$/);
assert.match(textbook_id,/^[a-f0-9-]{36}$/);
const [domain,section]=objective.split('.');
const request={topic,limit:8,mode:'NCE',domain,section,objective,format,item_id:process.env.SRNA_STAGING_ACCEPTANCE_ITEM_ID||crypto.randomUUID(),textbook_id};
// No-cost full-library preflight proves the multi-book path without forcing
// every generated question to cite books that do not help its particular claim.
const library=await call('/generation/textbooks');
if(process.argv.includes('--warmup-only')){
 console.log('Authenticated read-only staging warm-up completed; no model calls or draft writes');
 process.exit(0);
}
const books=library.textbooks.map(b=>b.id);
// Match the studio default: search all owned indexed books for generation too.
request.textbook_ids=books;
const multi=await call('/generation/preflight',{...request,textbook_ids:books});
assert.ok(multi.source_textbook_count>1,'Multi-book evidence packet collapsed to one book');
console.log(JSON.stringify({check:'multi_book_preflight',source_textbook_count:multi.source_textbook_count,passage_count:multi.passage_count,paid_calls:0}));
// Exercise actual PDF/PPTX extraction with synthetic curriculum outlines.
// Fixture bytes exist only on this disposable runner and contain no user data.
if(process.env.SRNA_STAGING_LECTURE_FIXTURES){
 const {readFile}=await import('node:fs/promises');
 const fixtures=JSON.parse(await readFile(process.env.SRNA_STAGING_LECTURE_FIXTURES,'utf8'));
 for(const fixture of fixtures){
  for(const fmt of [format]){
   const plan=await call('/generation/lecture-file-plan',{...fixture,textbook_id:'all',count:3,mode:'NCE',format:fmt,domain:'I',section:'C',objective:'I.C.5'});
   assert.equal(plan.database_writes,false);assert.equal(plan.auto_generate,false);assert.equal(plan.auto_publish,false);
   assert.equal(plan.count,3,'Lecture request did not honor its three-question allocation');
   assert.ok(plan.jobs.every(j=>j.body.format===fmt&&j.path==='/generation/preflight'));
   assert.ok(plan.jobs.some(j=>j.body.textbook_ids?.length>1),'Lecture job lost multi-book evidence');
   console.log(JSON.stringify({check:'lecture_file_plan',extension:fixture.filename.split('.').pop(),format:fmt,jobs:plan.count,paid_calls:0}));
  }
 }
}
const unsupported=await call('/generation/lecture-plan',{lecture_text:'# Quantum banana unicorn transport',textbook_id:request.textbook_id,count:1,mode:'NCE',format,domain:'I',section:'C',objective:'I.C.5'});
assert.equal(unsupported.count,0,'Unsupported lecture topic reached generation');
console.log('Unsupported lecture concept held without paid generation');

const preflight=multi;
assert.equal(preflight.dry_run,true);assert.equal(preflight.can_publish,false);
assert.ok(preflight.passage_count>0,'No indexed evidence');
assert.equal(preflight.review_readiness?.blind_review,'configured');
assert.equal(preflight.review_readiness?.rewrite,'configured');
assert.equal(preflight.review_readiness?.independent_option_review,'configured');
assert.equal(preflight.review_readiness?.explanation_review,'configured');
assert.equal(preflight.review_readiness?.board_quality_review,'configured');
assert.equal(preflight.quality_contract,'2026-11-10-v2');
assert.equal(preflight.authoring_contract,'2026-11-19-v26');
assert.equal(preflight.authoring_provider,'cloudflare');
assert.equal(preflight.authoring_delivery_model,'@cf/zai-org/glm-5.3');
if(!paid){console.log('Read-only generator acceptance passed; no model calls or draft writes');process.exit(0);}
const semanticReady=await call('/generation/index-readiness');
assert.equal(semanticReady.ready,true,'Complete canonical semantic index required before paid acceptance');
assert.equal(semanticReady.inventory_digest,preflight.semantic_inventory?.inventory_digest,'Runtime and indexed canonical inventory differ');
console.log(JSON.stringify({check:'semantic_index_readiness',expected_count:semanticReady.expected_count,indexed_count:semanticReady.indexed_count,ready:true}));
const checkpointReady=await call('/generation/checkpoint-readiness');
assert.equal(checkpointReady.ready,true,'Existing checkpoint storage is unavailable');
assert.ok(preflight.resume,'Runtime checkpoint recovery is disabled');
if(process.env.SRNA_STAGING_ACCEPTANCE_ITEM_ID){
 assert.equal(preflight.resume.completed,true,'Recovery is allowed only for a proven completed result; no duplicate paid generation');
}
console.log(JSON.stringify({acceptance_item_id:request.item_id,recovering_completed:preflight.resume.completed===true}));
console.log('Indexed textbook evidence and independent review configuration verified');
const connection=await call('/generation/provider-check');
assert.equal(connection.container_relay,'OK');
assert.equal(connection.metadata_ready,true);
assert.ok(connection.providers.every(p=>p.provider!=='gemini'));
console.log('Signed container relay and active provider metadata verified');
let generated;
try{generated=await call('/generation/one',{...request,...(process.env.SRNA_STAGING_ACCEPTANCE_ITEM_ID?{resume_completed_only:true}:{})});}
catch(error){if(!isGenerationDisconnect(error))throw error;console.log('Generation connection interrupted; checking only the existing completed checkpoint');generated=await recoverCompletedGeneration(request,cached=>call('/generation/one',cached));}
assert.equal(generated.can_publish,false);assert.equal(generated.published,false);
assert.equal(generated.dry_run,false);assert.ok(generated.item);
assert.match(generated.draft_id,/^[a-f0-9-]{36}$/);
const saved=await call('/generation/drafts/'+generated.draft_id);
assert.equal(saved.draft_id,generated.draft_id);
const current=await call('/generation/drafts/'+generated.draft_id+'/revalidate');
assert.equal(current.generation_performed,false);
assert.equal(current.database_writes,false);
assert.equal(current.published,false);
assert.equal(current.can_publish,false);
assert.equal(current.clinical_review_required,true);
assert.ok(Array.isArray(current.issues));
console.log(JSON.stringify({check:'current_index_revalidation',issues:current.issues.length,rules:current.issues.map(issue=>issue.rule_id)}));
assert.equal(current.issues.length,0,'Saved draft did not pass current-index approval revalidation');
const stages=Object.fromEntries(Object.entries(generated.screening?.stages||{}).map(([name,s])=>[name,s.status]));
console.log(JSON.stringify({draft_id:generated.draft_id,status:saved.status,published:false,stages,generator_issue_rules:(generated.generator_issues||[]).map(i=>i.rule_id),rewrite_attempts:generated.screening?.rewrite_attempts_used}));
assert.equal(saved.status,'pending_review','Draft still requires automated revision');
if(['MC','MS'].includes(format)){
assert.equal(stages.editorial_quality,'pass','Independent item-writing quality review did not pass');
assert.equal(generated.screening.stages.editorial_quality.counterfactual_verification?.status,'pass','Changed stem did not independently yield a new correct answer');
assert.equal(stages.options_only,'pass','Repeated options-only cue screening did not pass');
assert.equal(saved.question?.self_check?.recorded_by||saved.item?.self_check?.recorded_by||generated.item?.self_check?.recorded_by,'trusted_screening');
assert.equal(generated.item.options.find(o=>generated.item.key.includes(o.id)).error_pattern,null);
}
assert.equal(stages.explanation_evidence,'pass','Concept and rationale source review did not pass');
assert.equal(stages.schema,'pass','Generated schema did not pass');
assert.equal(stages.deterministic_text,'pass','Deterministic wording screening did not pass');
assert.equal(stages.evidence,'pass','Evidence validation did not pass');
assert.equal(stages.duplicates,'pass','Canonical semantic duplicate screening did not pass');
assert.equal(stages.blind_model,'pass','Independent blind review did not pass');
if(['MC','MS'].includes(format)){
assert.equal(stages.independent_option_evidence,'pass','Independent source-grounded option review did not complete');
assert.equal(generated.screening?.independent_option_adjudication?.clinical_truth_verified,false);
assert.equal(generated.screening?.independent_option_adjudication?.human_review_required,true);
}
assert.equal((generated.generator_issues||[]).length,0,'Unresolved generator issues');
console.log('One authenticated textbook-grounded question persisted as an unpublished draft');
