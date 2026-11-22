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
const before = await manage({action:'status'});
assert.ok(!before.batch || ['complete','cancelled'].includes(before.batch.status),'Another batch is active');

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
const plan = await call('/generation/lecture-plan',{
 lecture_text,textbook_id:'all',count:25,mode:'NCE',format:'MC',
 domain:'II',section:'C',objective:'II.C.4',
});
assert.equal(plan.count,25,'Expected 25 textbook-grounded slots');
assert.equal(plan.paid_calls_requested,false);
assert.equal(plan.jobs.length,25);
const jobs = plan.jobs.map(job => job.body);
assert.ok(new Set(jobs.map(job => job.topic)).size >= 4,'Expected varied covered lecture concepts');
const preflight = await call('/generation/preflight',jobs[0]);
assert.equal(preflight.authoring_contract,'2026-11-21-v48');
assert.ok(preflight.passage_count > 0);
const id = '562a335a-27dd-4721-abab-8f99fca72c30';
const {batch:queued} = await manage({action:'start',id,count:25,jobs,confirm:true});
assert.equal(queued.id,id);
assert.equal(queued.items.length,25);
console.log(JSON.stringify({check:'background_batch_queued',id,attempts:queued.items.length,first_item_id:queued.items[0].id}));
await wait(10000);
const {batch} = await manage({action:'status'});
assert.equal(batch.id,id);
console.log(JSON.stringify({check:'background_batch_status',id,status:batch.status,counts:batch.items.reduce((counts,item)=>({...counts,[item.status]:(counts[item.status]||0)+1}),{})}));
