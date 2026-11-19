import assert from 'node:assert/strict';
import {test} from 'node:test';
import {verifySavedReview} from './verify-saved-staging-option-review.mjs';
const sha='b'.repeat(40),image='a'.repeat(64),time=1800000000000;
const env={CONFIRM_PAID_OPTION_REVIEW:'true',STAGING_SAVED_DRAFT_ID:'65c2e793-a7af-4746-bfb6-1abf9993085c',STAGING_TARGET_SHA:sha,STAGING_TARGET_BUILD_UUID:'409749dd-864f-40a6-8389-e0884d20bcdc',STAGING_TARGET_IMAGE_SHA256:image,
 CLOUDFLARE_ACCOUNT_ID:'a'.repeat(32),CLOUDFLARE_API_TOKEN:'fixture',GITHUB_TOKEN:'fixture',SRNA_STAGING_REVIEWER_ACCESS_TOKEN:'fixture',STAGING_SUPABASE_ANON_KEY:'fixture'};
function fixture(mode='pass'){
 const calls=[],logs=[];let written=false;
 const stages={schema:{status:'pass'},options_only:{status:'pass'},human_review:{status:'pending'},independent_option_evidence:{status:'pending'}};
 const before={published:false,status:'pending_review',format:'MC',can_complete_option_review:true,updated_at:'version',question:{stem:'Synthetic case',key:['A']},screening:{rewrite_attempts_used:1,stages}};
 const result={published:false,can_publish:false,question_modified:false,generation_performed:false,rewrite_performed:false,clinical_review_required:true,automated_checks_passed:mode!=='pending',option_review_status:mode==='pending'?'pending':'pass'};
 const fetchImpl=async(url,options={})=>{
  calls.push({url,method:options.method||'GET'});let data;
  if(url.includes('/git/ref/'))data={object:{sha:mode==='stale'?'c'.repeat(40):sha}};
  else if(url.includes('/builds/builds/'))data={success:true,result:{status:'stopped',build_outcome:mode==='bad-build'?'failure':'success',build_trigger_metadata:{commit_hash:sha},stopped_on:new Date(time-180000).toISOString()}};
  else if(url.includes('api.cloudflare.com'))data={success:true,result:url.endsWith('/instances-v2')?[]:{updated_at:new Date(time-120000).toISOString(),health:{errors:[]},configuration:{image:'registry/image@sha256:'+image}}};
  else if(url.endsWith('/auth/v1/user'))data={id:'c003287a-10ce-4cc9-926e-ef7c3a162a26'};
  else if(url.endsWith('/complete-options')){
   if(mode==='timeout')throw Error('Simulated transport failure');
   assert.deepEqual(JSON.parse(options.body),{confirm_paid_calls:true,expected_updated_at:'version'});written=true;data=mode==='unsafe'?{...result,rewrite_performed:true}:result;
  }else if(url.endsWith('/revalidate'))data={published:false,generation_performed:false,database_writes:false,issues:written&&mode!=='pending'?[]:[{rule_id:'R-12.10',field:'screening.stages.independent_option_evidence'}]};
  else data=written?{...before,screening:{...before.screening,stages:{...stages,independent_option_evidence:{status:mode==='pending'?'pending':'pass'}}}}:before;
  return Response.json(data);
 };
 const deployment={verification:'connected_cloudflare_deployment_read',verified_at:new Date(mode==='expired'?time-300001:time).toISOString(),build:{build_uuid:env.STAGING_TARGET_BUILD_UUID,status:'stopped',build_outcome:mode==='bad-build'?'failure':'success',commit_hash:sha,stopped_on:new Date(time-180000).toISOString()},app:{updated_at:new Date(time-120000).toISOString(),health:{errors:[]},configuration:{image:'registry/image@sha256:'+image}},instances:[]};
 return {calls,logs,run:overrides=>verifySavedReview({env:{...env,...overrides},fetchImpl,emit:v=>logs.push(v),now:()=>time,deployment})};
}
test('saved review acceptance performs one paid review, preserves question and never invokes authoring or approval',async()=>{
 const f=fixture();const result=await f.run();assert.equal(result.question_unchanged,true);
 const posts=f.calls.filter(c=>c.method==='POST');assert.equal(posts.length,1);assert.ok(posts[0].url.endsWith('/complete-options'));
 assert.ok(f.calls.every(c=>!c.url.endsWith('/generation/one')&&!c.url.endsWith('/review')));
 assert.equal(f.logs.at(-1).published,false);assert.equal(f.logs.at(-1).rewrite_attempts,1);
});
test('stale staging code or absent confirmation stops before any paid request',async()=>{
 const unconfirmed=fixture();await assert.rejects(unconfirmed.run({CONFIRM_PAID_OPTION_REVIEW:'false'}));assert.equal(unconfirmed.calls.filter(c=>c.method==='POST').length,0);
 for(const mode of ['stale','bad-build','expired']){const f=fixture(mode);await assert.rejects(f.run());assert.equal(f.calls.filter(c=>c.method==='POST').length,0);}
});
test('transport errors and a blocked clinical review are not retried or reported as acceptance',async()=>{
 for(const mode of ['timeout','pending','unsafe']){
  const f=fixture(mode);await assert.rejects(f.run());assert.equal(f.calls.filter(c=>c.method==='POST').length,1);
  if(mode==='pending')assert.equal(f.logs.at(-1).automated_checks_passed,false);
 }
});
