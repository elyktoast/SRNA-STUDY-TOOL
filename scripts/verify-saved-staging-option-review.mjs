// Explicit paid REVIEW only. Never generate, rewrite, approve or publish.
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {settled,completedWorkerBuild} from './wait-staging-reviewer-rollout.mjs';
const project='https://xqyasyambwdyhsjkftqu.supabase.co';
const gateway='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const repo='https://api.github.com/repos/elyktoast/SRNA-STUDY-TOOL';
const owner='c003287a-10ce-4cc9-926e-ef7c3a162a26';
const canonical=value=>value&&typeof value==='object'?(Array.isArray(value)?value.map(canonical):Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]))):value;
const digest=value=>createHash('sha256').update(JSON.stringify(canonical(value))).digest('hex');

export async function verifySavedReview({env=process.env,fetchImpl=fetch,emit=value=>console.log(JSON.stringify(value)),now=Date.now}={}){
 assert.equal(env.CONFIRM_PAID_OPTION_REVIEW,'true','Explicit paid option-review confirmation required');
 const id=env.STAGING_SAVED_DRAFT_ID,sha=env.STAGING_TARGET_SHA,image=env.STAGING_TARGET_IMAGE_SHA256;
 assert.match(id||'',/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/);
 assert.match(sha||'',/^[a-f0-9]{40}$/);assert.match(image||'',/^[a-f0-9]{64}$/);
 const json=async(url,options={})=>{
  const response=await fetchImpl(url,{...options,redirect:'error',signal:AbortSignal.timeout(240000)});
  const data=await response.json().catch(()=>null);
  assert.ok(response.ok&&data,'Authenticated staging verification request failed: HTTP '+response.status);
  return data;
 };
 const gh={Authorization:'Bearer '+env.GITHUB_TOKEN,Accept:'application/vnd.github+json'};
 const head=await json(repo+'/git/ref/heads/fix/board-question-quality',{headers:gh});
 assert.equal(head.object?.sha,sha,'Staging code changed; do not perform a paid review');
 const checks=await json(repo+'/commits/'+sha+'/check-runs?per_page=100',{headers:gh});
 const completed=completedWorkerBuild(checks.check_runs,sha);assert.notEqual(completed,null,'Exact staging Worker build has not completed');
 assert.match(env.CLOUDFLARE_ACCOUNT_ID||'',/^[a-f0-9]{32}$/);
 const cf='https://api.cloudflare.com/client/v4/accounts/'+env.CLOUDFLARE_ACCOUNT_ID+'/containers/applications/a03bdc12-da09-4e2c-b543-816ebad2e339';
 const cfHeaders={Authorization:'Bearer '+env.CLOUDFLARE_API_TOKEN};
 const [app,instances]=await Promise.all([json(cf,{headers:cfHeaders}),json(cf+'/instances-v2',{headers:cfHeaders})]);
 assert.equal(app.success,true);assert.equal(instances.success,true);
 assert.ok(app.result.configuration.image.endsWith('@sha256:'+image),'Unexpected staging container image');
 assert.ok(settled(app.result,instances.result,now(),now()-90000,completed),'Staging rollout is not settled');
 let token=env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
 if(env.STAGING_TEST_ADMIN_EMAIL&&env.STAGING_TEST_ADMIN_PASSWORD){
  const login=await json(project+'/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:env.STAGING_SUPABASE_ANON_KEY,'Content-Type':'application/json'},body:JSON.stringify({email:env.STAGING_TEST_ADMIN_EMAIL,password:env.STAGING_TEST_ADMIN_PASSWORD})});
  token=login.access_token;
 }
 assert.ok(token&&env.STAGING_SUPABASE_ANON_KEY,'Staging administrator credentials unavailable');
 const identity=await json(project+'/auth/v1/user',{headers:{apikey:env.STAGING_SUPABASE_ANON_KEY,Authorization:'Bearer '+token}});
 assert.equal(identity.id,owner,'Only the configured textbook owner may run this acceptance');
 const headers={Origin:'https://staging.srnastudytool.com',Authorization:'Bearer '+token,'Content-Type':'application/json'};
 const path='/generation/drafts/'+id;
 const before=await json(gateway+path,{headers});
 assert.equal(before.published,false);assert.equal(before.status,'pending_review');assert.equal(before.format,'MC');
 assert.equal(before.can_complete_option_review,true,'Saved question is not eligible for a missing review');
 const baseline=await json(gateway+path+'/revalidate',{headers});
 assert.ok(Array.isArray(baseline.issues)&&baseline.issues.length>0&&baseline.issues.every(i=>i.field==='screening.stages.independent_option_evidence'),'Saved question has other unresolved issues');
 const questionHash=digest(before.question),rewrites=before.screening.rewrite_attempts_used;
 // Exactly one POST. Timeouts and provider failures never repeat the paid action.
 const result=await json(gateway+path+'/complete-options',{method:'POST',headers,body:JSON.stringify({confirm_paid_calls:true,expected_updated_at:before.updated_at})});
 for(const key of ['published','can_publish','question_modified','generation_performed','rewrite_performed'])assert.equal(result[key],false);
 assert.equal(result.clinical_review_required,true);
 const after=await json(gateway+path,{headers});
 assert.equal(digest(after.question),questionHash,'Saved question changed during review');
 assert.equal(after.screening.rewrite_attempts_used,rewrites,'Rewrite budget changed');
 assert.equal(after.screening.stages.human_review.status,before.screening.stages.human_review.status);
 assert.equal(after.status,'pending_review');assert.equal(after.published,false);
 const current=await json(gateway+path+'/revalidate',{headers});
 assert.equal(current.generation_performed,false);assert.equal(current.database_writes,false);assert.equal(current.published,false);
 const stages=Object.fromEntries(Object.entries(after.screening.stages).map(([name,value])=>[name,value.status]));
 emit({draft_id:id,question_sha256:questionHash,question_unchanged:true,rewrite_attempts:rewrites,
  review_status:result.option_review_status,automated_checks_passed:result.automated_checks_passed,
  stages,current_index_issue_rules:current.issues.map(i=>i.rule_id),generation_performed:false,rewrite_performed:false,published:false});
 assert.equal(result.automated_checks_passed,true,'Missing review completed but question remains blocked');
 assert.equal(current.issues.length,0,'Current-source approval revalidation has unresolved issues');
 return {draft_id:id,question_unchanged:true,published:false};
}
if(process.argv[1]&&import.meta.url===pathToFileURL(process.argv[1]).href)await verifySavedReview();
