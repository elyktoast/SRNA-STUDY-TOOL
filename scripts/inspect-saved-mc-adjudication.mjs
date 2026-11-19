// Read-only diagnosis: no generation, review, rewriting, approval or publication.
import assert from 'node:assert/strict';
const env=process.env,base='https://xqyasyambwdyhsjkftqu.supabase.co';
async function read(url,options={}){const r=await fetch(url,{...options,redirect:'error',signal:AbortSignal.timeout(30000)});assert.ok(r.ok,'Read unavailable: HTTP '+r.status);return r.json();}
const key=env.STAGING_SUPABASE_ANON_KEY;assert.ok(key);
let token=env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
if(env.STAGING_TEST_ADMIN_EMAIL&&env.STAGING_TEST_ADMIN_PASSWORD){const r=await read(base+'/auth/v1/token?grant_type=password',{method:'POST',headers:{apikey:key,'Content-Type':'application/json'},body:JSON.stringify({email:env.STAGING_TEST_ADMIN_EMAIL,password:env.STAGING_TEST_ADMIN_PASSWORD})});token=r.access_token;}
const identity=await read(base+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token}});
assert.equal(identity.id,'c003287a-10ce-4cc9-926e-ef7c3a162a26');
const id='0db56e8d-41ec-4f99-9276-e88c31aaee1c';
const draft=await read('https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/generation/drafts/'+id,{headers:{Authorization:'Bearer '+token,Origin:'https://staging.srnastudytool.com'}});
assert.equal(draft.published,false);
const report=draft.screening.independent_option_adjudication;
console.log(JSON.stringify({draft_id:id,published:false,model_calls:0,database_writes:false,report_status:report.status,
 judgments:report.judgments?.map(j=>({option_id:j.option_id,verdict:j.verdict,explanation:j.explanation,source_conflict_found:j.source_conflict_found,passage_ids:j.passage_ids,quote_count:j.quotes?.length})),issues:report.issues}));
