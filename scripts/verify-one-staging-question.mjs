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
 const r=await fetch(gateway+path,{method:body?'POST':'GET',headers,redirect:'error',...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(path==='/generation/one'?480000:240000)});
 const data=await r.json().catch(()=>null);
 if(!data)throw Error('Staging acceptance received a non-JSON response: HTTP '+r.status);
 if(!r.ok){
  // Only fixed machine-readable categories; never log provider output or evidence.
  const safe=v=>typeof v==='string'&&/^[A-Za-z0-9_]{1,80}$/.test(v)?v:'UNCLASSIFIED';
  console.log(JSON.stringify({path,status:r.status,error:safe(data.error),rule:safe(data.rule),failed_step:safe(data.failed_step),validation_detail:safe(data.validation_detail),validation_contract:typeof data.validation_contract==='string'&&/^2026-11-10-v[0-9]{1,2}$/.test(data.validation_contract)?data.validation_contract:'UNCLASSIFIED'}));
  throw Error('Staging acceptance request failed: HTTP '+r.status);
 }
 return data;
}
// Keep earlier recovery failures visibly flagged; this is an automated defect
// report under the authenticated owner account, never human clinical approval.
for(const [id,reason] of [
 ['61de5636-3aa5-46b9-88ba-79bf8a75cfa6','Changed-stem verification correctly found three defensible answers; one rewrite also retained an answer cue. Not accepted as a board-quality milestone.'],
 ['34c128dd-8586-47f8-b7bd-1a8af8d6d2e4','Recall-only question with an ambiguous distractor, unverified equation and an ineffective counterfactual; rejected after the single rewrite.'],
 ['49551d1a-01a6-483a-b9e6-59c892a01ad9','Counterfactual not bound to a finished stem, incomplete source review, and unnecessary unverified pressure values; rejected after one rewrite.'],
 ['d9da16d9-6134-4688-b033-82debbfd0abe','The client timed out, but the backend saved a candidate that still failed its counterfactual and unverified equation checks.'],
 ['782dcc83-a42c-432f-9864-8578ad0ea84e','The question embeds its counterfactual as an implausible disease transition and contains an unverified reversed formula; not accepted as a board-quality question.'],
 ['e530328c-3266-4671-b12b-df732b5c783b','Recall-only candidate with a second defensible choice, ineffective counterfactual and options-only cue; failed acceptance after its single rewrite.'],
 ['df490c7f-4a85-4eb8-9b97-740b2a2910bc','Blind answer disagreement, unsupported distractor claim and a counterfactual absent from the stem; rejected after one rewrite.'],
 ['dd641cda-00c4-49b9-9fdf-5ce19620fb9b','Failed application-level reasoning, counterfactual verification and affirmative distractor support after its single rewrite.'],
 ['478fd4be-b899-41ec-8c71-2d470feba9b5','Counterfactual still failed after one rewrite and source explanation review was truncated; not accepted as a quality milestone.'],
 ['5cdb6e33-d6f5-426a-9fd2-42e88dd597ad','Recall candidate retained a failed changed-stem blind result, unverified worded equation and incomplete source explanation review after its one rewrite.'],
 ['b9880dde-631b-41a2-b684-c57871f89770','The only rewrite retained unsupported distractor explanations and an options-only answer cue; counterfactual wording did not actually change the keyed decision.'],
 ['2b7f969b-b9f0-4ed4-9131-e84e0b325a37','Full v2.0 audit found obsolete halothane, incorrect airway blueprint classification, an ineffective counterfactual and faulty trap logic.'],
 ['97a2f6e0-e2e9-40a5-bb63-e29827aeff5e','Final source QA found named drug examples absent from the cited class-only passage; requires indexed support for their class membership.'],
 ['038defcb-295a-43a9-bdb4-5bb6a310b183','Text-only draft omitted its required item-level verification flag.'],
 ['11d8fe2a-af0c-4986-ab17-f1524eb2fe1a','The guarded rewrite omitted required option error_pattern tags; quality validation failed.'],
 ['273d8969-5957-4aec-9c4d-7c46548de822','Option evidence remained unsupported after the single rewrite; quality validation failed.'],
 ['217c7f66-65ff-4c4a-849a-09598f6c26c1','The single rewrite still relied on source silence to reject distractors; quality validation failed.'],
 ['bb4d1576-3ca2-4c7d-b539-56520e861957','The generated draft retained an answer-length cue and did not complete exact-quote source adjudication.'],
 ['0e4a82b6-0d86-49c0-9868-17ac8f365d3c','The earlier explanation review and short-label wording screening did not pass.'],
 ['7bbe5981-ca10-4da8-a734-5dbbbda8d0d1','Ambiguous single-answer question had two source-supported answers; the earlier bounded repair was rate-limited.'],
 ['83916827-3192-45ab-806e-c81e2f26ba04','Independent source review was rate-limited; the draft also introduced mechanistic background beyond its supplied classification excerpt.'],
 ['eec2209c-419d-40ea-b830-6586d2b06125','Citation/quotation validation and guarded rewrite failed.'],
 ['d87e0523-a4bd-40a9-8f61-cdaabd6ad297','Another option is also source-supported; the primary/secondary ranking is unsupported.']
]){
 const previous=await call('/generation/drafts/'+id);
 if(previous.status==='pending_review'){
  const flagged=await call('/generation/drafts/'+id+'/review',{status:'needs_revision',notes:'Automated recovery QA: '+reason+' Kept unpublished; no human clinical approval performed.'});
  assert.equal(flagged.status,'needs_revision');assert.equal(flagged.published,false);
 }
}
// Append a source-faithful correction; keep the original generated question immutable.
const recoveredDraft='e9ee3c59-0924-402c-9501-63464d53ffdb';
const revisionState=await call('/generation/drafts/'+recoveredDraft+'/revisions');
const relevance='Selecting nontriggering anesthetic agents is important for patients susceptible to malignant hyperthermia. The supplied table classifies volatile inhalation anesthetics and succinylcholine as triggering, and local anesthetics, opioids and nitrous oxide as nontriggering.';
if(revisionState.current_question?.concept_card?.relevance!==relevance){
 const revised=await call('/generation/drafts/'+recoveredDraft+'/revisions',{
  expected_parent_sha256:revisionState.current_question_sha256,citation_excerpts:{},option_evidence:{},
  question_edits:{concept_card:{relevance}},
  reviewer_notes:'Automated source-grounded editorial correction removes an unsupported inventory prohibition. Original retained; human clinical and blueprint review still required. No publication or clinical approval.'
 });
 assert.equal(revised.published,false);assert.equal(revised.can_publish,false);assert.equal(revised.clinical_review_required,true);
 const verified=await call('/generation/drafts/'+recoveredDraft+'/revisions');
 assert.equal(verified.current_question.concept_card.relevance,relevance);
 assert.deepEqual(verified.current_question.key,revisionState.current_question.key);
 const digest=async value=>Buffer.from(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value)))).toString('hex');
 assert.equal(await digest(verified.current_question.evidence),await digest(revisionState.current_question.evidence),'Revision changed source references');
 console.log(JSON.stringify({corrected_draft:recoveredDraft,revision_id:revised.revision_id,published:false,human_review_required:true}));
}
const request={topic:'"dynamic compliance" OR "static compliance"',limit:2,page_start:731,page_end:732,mode:'NCE',domain:'I',section:'A',objective:'I.A.2',format:'MC',item_id:process.env.SRNA_STAGING_ACCEPTANCE_ITEM_ID||crypto.randomUUID(),textbook_id:'6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d'};
const preflight=await call('/generation/preflight',request);
assert.equal(preflight.dry_run,true);assert.equal(preflight.can_publish,false);
assert.ok(preflight.passage_count>0,'No indexed evidence');
assert.equal(preflight.review_readiness?.blind_review,'configured');
assert.equal(preflight.review_readiness?.rewrite,'configured');
assert.equal(preflight.review_readiness?.independent_option_review,'configured');
assert.equal(preflight.review_readiness?.explanation_review,'configured');
assert.equal(preflight.review_readiness?.board_quality_review,'configured');
assert.equal(preflight.quality_contract,'2026-11-10-v2');
assert.equal(preflight.authoring_contract,'2026-11-10-v11');
assert.equal(preflight.authoring_provider,'cloudflare');
assert.equal(preflight.authoring_delivery_model,'@cf/openai/gpt-oss-120b');
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
const generated=await call('/generation/one',request);
assert.equal(generated.can_publish,false);assert.equal(generated.published,false);
assert.equal(generated.dry_run,false);assert.ok(generated.item);
assert.match(generated.draft_id,/^[a-f0-9-]{36}$/);
const saved=await call('/generation/drafts/'+generated.draft_id);
assert.equal(saved.draft_id,generated.draft_id);
assert.equal(saved.status,'pending_review');
const stages=Object.fromEntries(Object.entries(generated.screening?.stages||{}).map(([name,s])=>[name,s.status]));
console.log(JSON.stringify({draft_id:generated.draft_id,status:saved.status,published:false,stages,generator_issue_rules:(generated.generator_issues||[]).map(i=>i.rule_id),rewrite_attempts:generated.screening?.rewrite_attempts_used}));
assert.equal(stages.editorial_quality,'pass','Independent item-writing quality review did not pass');
assert.equal(generated.screening.stages.editorial_quality.counterfactual_verification?.status,'pass','Changed stem did not independently yield a new correct answer');
assert.equal(stages.options_only,'pass','Repeated options-only cue screening did not pass');
assert.equal(saved.question?.self_check?.recorded_by||saved.item?.self_check?.recorded_by||generated.item?.self_check?.recorded_by,'trusted_screening');
assert.equal(generated.item.options.find(o=>generated.item.key.includes(o.id)).error_pattern,null);
assert.equal(stages.explanation_evidence,'pass','Concept and rationale source review did not pass');
assert.equal(stages.schema,'pass','Generated schema did not pass');
assert.equal(stages.deterministic_text,'pass','Deterministic wording screening did not pass');
assert.equal(stages.evidence,'pass','Evidence validation did not pass');
assert.equal(stages.blind_model,'pass','Independent blind review did not pass');
assert.equal(stages.independent_option_evidence,'pass','Independent source-grounded option review did not complete');
assert.equal(generated.screening?.independent_option_adjudication?.clinical_truth_verified,false);
assert.equal(generated.screening?.independent_option_adjudication?.human_review_required,true);
assert.equal((generated.generator_issues||[]).length,0,'Unresolved generator issues');
console.log('One authenticated textbook-grounded question persisted as an unpublished draft');
