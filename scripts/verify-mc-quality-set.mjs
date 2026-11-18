// Fixed staging MC set: one request per topic; no rerolls, approval or publication.
import assert from 'node:assert/strict';
import {stagingFetch as fetch} from './staging-http-request.mjs';
import {readFileSync,writeFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {stagingReadOnlyRetry} from './staging-read-only-retry.mjs';
import {isGenerationDisconnect,recoverCompletedGeneration} from '../equipment/assets/generation-completion-recovery.js';
import {settled} from './wait-staging-reviewer-rollout.mjs';
export const samples=[
 {name:'Oxygen supply pressure failure',objective:'II.A.6',workflow:'lecture',item_id:'3c5c8bd5-c708-48c0-b255-e219d20c6137',textbook_id:'8343459f-0595-4375-8ac6-7700e6792abe',topic:'Oxygen pressure failure'}
];
const gateway='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const project='https://xqyasyambwdyhsjkftqu.supabase.co';
const sha='d3e7dfa01bb7eae236a5dcbd7e986b0734d1af84';
const safe=v=>typeof v==='string'&&/^[A-Za-z0-9_.-]{1,120}$/.test(v)?v:undefined;
export function verifyDeployment(d,now=Date.now()){
 assert.equal(d.verification,'connected_cloudflare_deployment_read');
 const age=now-Date.parse(d.verified_at);assert.ok(age>=-60000&&age<=300000,'Deployment verification expired');
 assert.equal(d.build.commit_hash,sha);assert.equal(d.build.build_outcome,'success');assert.equal(d.build.status,'stopped');
 assert.ok(settled(d.app,d.instances,now,now-90000,Date.parse(d.build.stopped_on)),'Container rollout not settled');
}
export async function runSet({env=process.env,fetchImpl=fetch,deployment,emit=v=>console.log(JSON.stringify(v)),save=()=>{},now=Date.now}={}){
 assert.equal(env.CONFIRM_PAID_MC_SET,'true');assert.equal(env.GITHUB_RUN_ATTEMPT,'1','Do not rerun paid acceptance');
 verifyDeployment(deployment,now());
 const json=async(url,options={})=>{
  const response=await fetchImpl(url,{...options,redirect:'error',signal:AbortSignal.timeout(480000)});
  const body=await response.json().catch(()=>null);
  if(!response.ok||!body){const e=Error('Staging request blocked');e.status=response.status;e.rule=safe(body?.rule);e.details={http_status:response.status,rule:safe(body?.rule),validation_detail:safe(body?.validation_detail),failed_step:safe(body?.failed_step)};throw e;}
  return body;
 };
 const head=await json('https://api.github.com/repos/elyktoast/SRNA-STUDY-TOOL/git/ref/heads/fix/board-question-quality',{headers:{Authorization:'Bearer '+env.GITHUB_TOKEN,Accept:'application/vnd.github+json'}});
 assert.equal(head.object?.sha,sha,'Staging branch changed');
 let token=env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
 const key=env.STAGING_SUPABASE_ANON_KEY;assert.ok(key);
 if(env.STAGING_TEST_ADMIN_EMAIL&&env.STAGING_TEST_ADMIN_PASSWORD){
  const login=await json(project+'/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:key,'Content-Type':'application/json'},body:JSON.stringify({email:env.STAGING_TEST_ADMIN_EMAIL,password:env.STAGING_TEST_ADMIN_PASSWORD})});token=login.access_token;
 }
 assert.ok(token);
 const identity=await json(project+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token}});
 assert.equal(identity.id,'c003287a-10ce-4cc9-926e-ef7c3a162a26');
 const headers={Origin:'https://staging.srnastudytool.com',Authorization:'Bearer '+token,'Content-Type':'application/json'};
 const call=(path,body)=>stagingReadOnlyRetry(path,async()=>{
  try{return await json(gateway+path,{headers,...(body?{method:'POST',body:JSON.stringify(body)}:{})});}
  catch(error){
   if(error.code==='ECONNRESET')throw new TypeError('Network connection reset',{cause:error});
   throw error;
  }
 });
 const library=await call('/generation/textbooks');const books=library.textbooks.map(b=>b.id);assert.ok(books.length>=7);
 const rows=[];
 for(const sample of samples){
  const row={...sample,accepted:false,draft_id:null,published:false};rows.push(row);let stopAfterFailure=false;
  try{
   // Recheck the branch before EACH paid item; never regenerate a used checkpoint.
   const currentHead=await json('https://api.github.com/repos/elyktoast/SRNA-STUDY-TOOL/git/ref/heads/fix/board-question-quality',{headers:{Authorization:'Bearer '+env.GITHUB_TOKEN,Accept:'application/vnd.github+json'}});
   assert.equal(currentHead.object?.sha,sha);
   const [domain,section]=sample.objective.split('.');
   let request={topic:sample.topic,objective:sample.objective,domain,section,mode:'NCE',format:'MC',limit:8,item_id:sample.item_id,textbook_id:sample.textbook_id||books[0],textbook_ids:books};
   if(sample.workflow==='lecture'){
    const plan=await call('/generation/lecture-file-plan',{filename:'equipment-review-fixture.pdf',file_base64:'JVBERi0xLjcKJcK1wrYKCjEgMCBvYmoKPDwvVHlwZS9DYXRhbG9nL1BhZ2VzIDIgMCBSPj4KZW5kb2JqCgoyIDAgb2JqCjw8L1R5cGUvUGFnZXMvQ291bnQgMS9LaWRzWzQgMCBSXT4+CmVuZG9iagoKMyAwIG9iago8PC9Gb250PDwvaGVsdiA1IDAgUj4+Pj4KZW5kb2JqCgo0IDAgb2JqCjw8L1R5cGUvUGFnZS9NZWRpYUJveFswIDAgNTk1IDg0Ml0vUm90YXRlIDAvUmVzb3VyY2VzIDMgMCBSL1BhcmVudCAyIDAgUi9Db250ZW50c1s2IDAgUl0+PgplbmRvYmoKCjUgMCBvYmoKPDwvVHlwZS9Gb250L1N1YnR5cGUvVHlwZTEvQmFzZUZvbnQvSGVsdmV0aWNhL0VuY29kaW5nL1dpbkFuc2lFbmNvZGluZz4+CmVuZG9iagoKNiAwIG9iago8PC9MZW5ndGggMjM0L0ZpbHRlci9GbGF0ZURlY29kZT4+CnN0cmVhbQp42lWQsU7EMAyG9zyFZyQgdmK7kU4MCBY2pGwnhlNJxQADC8/P7/TgQFXVJO7/+XPSZ7rviSnjYaoL+SLUP9Lt23j/ImbqGx0PlW2YevFqS3ytGUuu6uxqzbO9mtrwKlkFdUNd3e9e+lPKdM16w1ypP6TjYZ71q2CuyLALyA2vS7bNxE44jT4NFC0ndNl88WYeHSR7dpkmxTVWSJkxCOu+v/AvKw3r5gXpsmfx/zZpf2zPdQZPvXoDuZ6rM4V93AJm3G8BRJEfm3AfQY/UNPmd6Z99WGMG2LbdHPe3oluRMX0fe3pO3yMoWf4KZW5kc3RyZWFtCmVuZG9iagoKeHJlZgowIDcKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDE2IDAwMDAwIG4gCjAwMDAwMDAwNjIgMDAwMDAgbiAKMDAwMDAwMDExNCAwMDAwMCBuIAowMDAwMDAwMTU1IDAwMDAwIG4gCjAwMDAwMDAyNjIgMDAwMDAgbiAKMDAwMDAwMDM1MSAwMDAwMCBuIAoKdHJhaWxlcgo8PC9TaXplIDcvUm9vdCAxIDAgUi9JRFs8QzM5MjU0MEU0NTc0QzM4NkMyQURDMkEyQzI5RUMzODg+PEU3MTVDQ0M5RjY4RDZENzExRTkxREUwODg3N0Q0RjkyPl0+PgpzdGFydHhyZWYKNjU0CiUlRU9GCg==',textbook_id:'all',count:1,mode:'NCE',format:'MC',domain,section,objective:sample.objective});
    assert.equal(plan.database_writes,false);assert.equal(plan.file_extraction?.format,'pdf');
    assert.equal(plan.file_extraction?.requires_visual_review,false);
    assert.equal(plan.auto_generate,false);assert.equal(plan.auto_publish,false);assert.equal(plan.count,1,'Lecture objective held');
    assert.equal(plan.jobs[0].path,'/generation/preflight');
    assert.equal(plan.jobs[0].body.topic,sample.topic,'Lecture planner changed the intended clinical topic');
    assert.equal(plan.jobs[0].body.objective,sample.objective,'Lecture planner changed the selected objective');
    emit({check:'uploaded_pdf_lecture_topic',topic:plan.jobs[0].body.topic,objective:plan.jobs[0].body.objective,paid_calls:0});
    request={...plan.jobs[0].body,item_id:sample.item_id};
   }
   const preflight=await call('/generation/preflight',request);
   assert.equal(preflight.authoring_contract,'2026-11-18-v24');assert.equal(preflight.authoring_provider,'cloudflare');
   assert.equal(preflight.authoring_delivery_model,'@cf/zai-org/glm-5.3');
   if(!sample.recover_only)assert.equal(preflight.resume?.resumable,false,'Existing checkpoint: no paid replay');
   const completed=()=>recoverCompletedGeneration(request,cached=>call('/generation/one',cached),{onProgress:()=>emit({check:'completed_only_recovery',item_id:request.item_id})});
   let generated;
   if(sample.recover_only)generated=await completed();
   else try{generated=await call('/generation/one',request);}
   catch(error){if(!isGenerationDisconnect(error))throw error;generated=await completed();}
   assert.equal(generated.published,false);assert.equal(generated.can_publish,false);assert.ok(generated.draft_id);
   row.draft_id=generated.draft_id;
   const saved=await call('/generation/drafts/'+row.draft_id);
   const screening=saved.screening||generated.screening;
   row.stages=Object.fromEntries(Object.entries(screening.stages).map(([k,v])=>[k,v.status]));
   row.blockers=Object.fromEntries(Object.entries(screening.stages).filter(([k,v])=>k!=='human_review'&&v.status!=='pass'));
   row.rewrite_attempts=screening.rewrite_attempts_used;
   assert.ok(row.rewrite_attempts<=1);assert.equal(saved.published,false);
   // Preserve exact reviewer blockers privately, excluding full textbook excerpts.
   const question=saved.question||generated.item;
   row.question={stem:question.stem,options:question.options,key:question.key,rationale:question.rationale};
   const current=await call('/generation/drafts/'+row.draft_id+'/revalidate');
   assert.equal(current.database_writes,false);assert.equal(current.generation_performed,false);assert.equal(current.published,false);
   row.current_source_issues=current.issues;
   const automated=Object.entries(row.stages).filter(([k])=>k!=='human_review');
   row.passing_checks=automated.filter(([,v])=>v==='pass').length;
   row.accepted=automated.length===10&&row.passing_checks===10&&current.issues.length===0;
  }catch(error){row.failure=error.details||{reason:error.message,cause_code:safe(error.cause?.code)};stopAfterFailure=!error.details?.http_status||error.details.http_status>=500||error.details.rule==='GENERATION_BUSY';}
  save(rows);emit({topic:row.name,item_id:row.item_id,draft_id:row.draft_id,accepted:row.accepted,passing_checks:row.passing_checks,stages:row.stages,rewrite_attempts:row.rewrite_attempts,source_issue_count:row.current_source_issues?.length,blocker_rules:Object.fromEntries(Object.entries(row.blockers||{}).map(([stage,value])=>[stage,(value.issues||[]).map(issue=>({rule_id:issue.rule_id,field:issue.field}))])),failure:row.failure,published:false});
  if(stopAfterFailure){
   for(const pending of samples.slice(rows.length))rows.push({...pending,accepted:false,draft_id:null,published:false,not_run:'Prior ambiguous runtime failure; do not overlap backend work'});
   save(rows);break;
  }
 }
 return rows;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href){
 const deployment=JSON.parse(readFileSync(new URL('../.github/staging-mc-quality-deployment.json',import.meta.url),'utf8'));
 await runSet({deployment,save:rows=>writeFileSync('/tmp/srna-mc-quality-results.json',JSON.stringify(rows,null,2))});
}
