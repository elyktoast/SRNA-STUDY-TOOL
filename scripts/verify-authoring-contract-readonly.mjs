// Explicit one-question acceptance run. Never retry paid generation or publish.
import assert from 'node:assert/strict';
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
  console.log(JSON.stringify({path,status:r.status,error:safe(data.error),rule:safe(data.rule),failed_step:safe(data.failed_step)}));
  throw Error('Staging acceptance request failed: HTTP '+r.status);
 }
 return data;
}
const request={topic:'"dynamic compliance" OR "static compliance"',limit:2,page_start:731,page_end:732,mode:'NCE',domain:'I',section:'A',objective:'I.A.2',format:'MC',item_id:crypto.randomUUID(),textbook_id:'6f1b2869-d6ad-4adf-a9d8-888e8a3d9b9d'};
const preflight=await call('/generation/preflight',request);
assert.equal(preflight.dry_run,true);assert.equal(preflight.database_writes,false);
assert.equal(preflight.can_publish,false);
assert.equal(preflight.authoring_contract,'2026-11-10-v17');
assert.equal(preflight.authoring_provider,'cloudflare');
assert.equal(preflight.authoring_delivery_model,'@cf/zai-org/glm-5.3');
assert.equal(preflight.quality_contract,'2026-11-10-v2');
console.log('Authenticated runtime authoring contract verified without AI calls');
