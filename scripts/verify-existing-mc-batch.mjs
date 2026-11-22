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

let batch;
for (let attempt = 0; attempt < 4; attempt++) {
 try {
  ({batch} = await manage({action:'status'}));
  break;
 } catch (error) {
  if (attempt === 3 || !/^Staging HTTP 50[234]/.test(error.message)) throw error;
  await wait(15000);
 }
}
assert.equal(batch?.id,'562a335a-27dd-4721-abab-8f99fca72c30');
assert.equal(batch?.items.length,25);
assert.ok(['running','complete','cancelled'].includes(batch.status),'Legacy pause still requires intervention');
const counts = {};
for (const item of batch.items) counts[item.status] = (counts[item.status] || 0) + 1;
console.log(JSON.stringify({status:batch.status,reason:batch.reason ?? null,counts,scheduled:Number.isFinite(batch.nextRunAt)}));
