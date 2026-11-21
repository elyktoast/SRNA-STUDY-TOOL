import assert from 'node:assert/strict';
import {randomUUID} from 'node:crypto';
import {setTimeout as wait} from 'node:timers/promises';
import {stagingFetch as fetch} from './staging-http-request.mjs';

const gateway = 'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const project = 'https://xqyasyambwdyhsjkftqu.supabase.co';
const origin = 'https://staging.srnastudytool.com';
const env = process.env;
assert.equal(env.GITHUB_RUN_ATTEMPT,'1');
let token = env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
async function json(url, options={}) {
 const response = await fetch(url,{redirect:'error',signal:AbortSignal.timeout(90000),...options});
 const result = await response.json().catch(() => null);
 if (!response.ok) {
  const rule = typeof result?.rule === 'string' && /^[A-Z_]{2,64}$/.test(result.rule) ? ' ' + result.rule : '';
  throw Error('Staging HTTP ' + response.status + rule);
 }
 return result;
}
if (env.STAGING_TEST_ADMIN_EMAIL && env.STAGING_TEST_ADMIN_PASSWORD) {
 const auth = await json(project+'/auth/v1/token?grant_type=password',{method:'POST',headers:{
  apikey:env.STAGING_SUPABASE_ANON_KEY,'Content-Type':'application/json'
 },body:JSON.stringify({email:env.STAGING_TEST_ADMIN_EMAIL,password:env.STAGING_TEST_ADMIN_PASSWORD})});
 token = auth.access_token;
}
assert.ok(token);
const identity = await json(project+'/auth/v1/user',{headers:{
 apikey:env.STAGING_SUPABASE_ANON_KEY,Authorization:'Bearer '+token,
}});
assert.equal(identity.id,'c003287a-10ce-4cc9-926e-ef7c3a162a26');
const headers = {Origin:origin,Authorization:'Bearer '+token,'Content-Type':'application/json'};
const call = (path,body) => json(gateway+path,{headers,...(body?{method:'POST',body:JSON.stringify(body)}:{})});
const manage = body => call('/generation/mc-batch',body);
const before = await manage({action:'status'});
assert.ok(!before.batch || ['complete','cancelled'].includes(before.batch.status),'Another batch is active');
const plan = await call('/generation/lecture-plan',{
 lecture_text:'Page 14:\n# Quantitative Monitoring: Electromyography\n• Record the evoked muscle action potential\nLecture bold: Quantitative Monitoring: Electromyography',
 textbook_id:'all',count:25,mode:'NCE',format:'MC',domain:'II',section:'C',objective:'II.C.4',
});
assert.equal(plan.count,25);
assert.equal(plan.paid_calls_requested,false);
const job = plan.jobs[0].body;
const preflight = await call('/generation/preflight',job);
assert.equal(preflight.authoring_contract,'2026-11-21-v47');
assert.ok(preflight.passage_count > 0);
console.log(JSON.stringify({check:'grounded_batch_plan',planned:plan.count,paid_calls:0}));
const id = randomUUID();
const {batch:queued} = await manage({action:'start',id,count:25,jobs:[job],confirm:true});
assert.equal(queued.id,id);
assert.equal(queued.items.length,1);
console.log(JSON.stringify({check:'background_batch_queued',id,item_id:queued.items[0].id,attempt_cap:1}));
let final;
for (let index=0; index<34; index++) {
 await wait(30000);
 try {
  const {batch} = await manage({action:'status'});
  assert.equal(batch?.id,id);
  if (!['running','cancelling'].includes(batch.status)) { final = batch; break; }
 } catch (error) {
  if (!/^Staging HTTP 50[0234]/.test(error.message) && error.name !== 'TimeoutError') throw error;
 }
}
assert.ok(final,'Batch is still running after the observation window');
const item = final.items[0];
console.log(JSON.stringify({check:'batch_result',status:final.status,item_status:item.status,draft_id:item.draftId,reason:item.reason}));
assert.ok(item.draftId,'No saved batch draft');
const draft = await call('/generation/drafts/'+item.draftId);
assert.equal(draft.published,false);
const stages = Object.fromEntries(Object.entries(draft.screening.stages).map(([key,value])=>[key,value.status]));
console.log(JSON.stringify({check:'batch_draft_review',stages,option_provider_rule:draft.screening.independent_option_adjudication?.provider_rule}));
assert.equal(item.status,'ready','Draft remains held by automated review');
assert.equal(Object.entries(stages).filter(([key,value])=>key!=='human_review'&&value==='pass').length,10);
