import assert from 'node:assert/strict';
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
const lecture_text = [
 '# Peripheral nerve stimulator setup',
 '• Electrode placement and stimulation site selection',
 '• Supramaximal stimulation and baseline twitch response',
 '# Neuromuscular stimulation patterns',
 '• Single twitch, train-of-four, tetanus, double-burst stimulation, and posttetanic count',
 '• Interpreting fade and depth of neuromuscular blockade',
 '# Qualitative twitch assessment',
 '• Visual and tactile assessment and their limitations',
 '# Monitoring for residual neuromuscular blockade',
 '• Train-of-four count, train-of-four ratio, and assessment of recovery',
 '# Quantitative Monitoring: Mechanomyography',
 '• Distinguish force measurement from other observable signals',
 '# Quantitative Monitoring: Acceleromyography',
 '• Compare acceleration-based and force-based measurement',
 '# Quantitative Monitoring: Electromyography',
 '• Identify the signal measured after evoked nerve stimulation',
 '# Quantitative Monitoring: Kinemyography',
 '• Distinguish motion transduction from recording muscle electrical activity',
 '# Quantitative Monitoring: Phonomyography',
 '• Identify the measured signal during evoked muscle contraction',
 '# Quantitative Monitoring: Compressomyography',
 '• Compare the measurement principle with other quantitative methods',
].join('\n');
const campaign = ["b323fbe5-bc83-473a-b782-92b642236578", "57122c9b-377f-4f73-98d7-d71b8981b071", "3d0082fb-9e28-4759-97c7-3e223fdaf103"].map((id,index)=>({id,count:[25,50,100][index]}));
const initial = process.env.START_MCBENCH === 'true';
const {batch:previous}=await manage({action:'status'});
const stage=campaign.findIndex(entry=>entry.id===previous?.id);
let next;
if(stage===-1){
 if(!initial || (previous && !['complete','cancelled'].includes(previous.status))){
  console.log(JSON.stringify({event:'blocked',reason:'outside_campaign',active:Boolean(previous&&!['complete','cancelled'].includes(previous.status))}));
  process.exit(0);
 }
 next=campaign[0];
 for(const draft of ['fae1144e-f9e1-4245-a70d-fb7fe3b5b22a','8ec6f64c-9767-4a88-8d7f-8780ad3431c9','41eca576-e288-49a2-a54e-37ebd986dcb2']){
  try{
   const r=await call('/generation/drafts/'+draft+'/complete-options',{accept_recovered_only:true});
   assert.equal(r.paid_review_performed,false);
   assert.equal(r.published,false);
   console.log(JSON.stringify({event:'recovered',draft,status:r.draft_status}));
  }catch(error){
   console.log(JSON.stringify({event:'recovered_held',draft,result:error.message}));
  }
 }
}else{
 const completed=previous.items.filter(item=>!['started','queued'].includes(item.status));
 const terminal=['complete','cancelled'].includes(previous.status);
 console.log(JSON.stringify({event:terminal?'terminal':'progress',id:previous.id,target:previous.requested,
   status:previous.status,reason:previous.reason,accepted:previous.acceptedCount,attempts:completed.length,
   deadline_at:previous.deadlineAt,observed_at:new Date().toISOString(),
   ...(terminal?{item_ids:completed.map(item=>item.id)}:{})}));
 if(!terminal || previous.status!=='complete' || previous.reason!=='target_reached' ||
    previous.acceptedCount!==previous.requested || stage===2)process.exit(0);
 next=campaign[stage+1];
}
const plan=await call('/generation/lecture-plan',{
 lecture_text,textbook_id:'all',count:next.count,mode:'NCE',format:'MC',domain:'II',section:'C',objective:'II.C.4',
});
assert.equal(plan.paid_calls_requested,false);
const jobs=plan.jobs.map(job=>job.body);
assert.ok(new Set(jobs.map(job=>job.topic)).size>=4,'Too few grounded lecture topics for safe benchmark');
const preflight=await call('/generation/preflight',jobs[0]);
assert.equal(preflight.authoring_contract,'2026-11-21-v48');
assert.ok(preflight.passage_count>0);
const startedAt=new Date().toISOString();
const {batch}=await manage({action:'start',id:next.id,count:next.count,jobs,goal:'accepted',confirm:true});
assert.equal(batch.id,next.id);
assert.equal(batch.goal,'accepted');
assert.equal(batch.attemptLimit,next.count*2);
console.log(JSON.stringify({event:'started',id:batch.id,target:batch.requested,planned:jobs.length,
 attempt_limit:batch.attemptLimit,started_at:startedAt,deadline_at:batch.deadlineAt}));
