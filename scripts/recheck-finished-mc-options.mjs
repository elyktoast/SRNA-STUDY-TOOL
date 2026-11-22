import assert from 'node:assert/strict';
const env = process.env;
const supabase = 'https://xqyasyambwdyhsjkftqu.supabase.co';
const gateway = 'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const key = env.STAGING_SUPABASE_ANON_KEY;
assert.ok(key);
let token = env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
if (env.STAGING_TEST_ADMIN_EMAIL && env.STAGING_TEST_ADMIN_PASSWORD) {
  const auth = await fetch(supabase + '/auth/v1/token?grant_type=password', {
    method:'POST', redirect:'error',
    headers:{apikey:key,'Content-Type':'application/json'},
    body:JSON.stringify({email:env.STAGING_TEST_ADMIN_EMAIL,password:env.STAGING_TEST_ADMIN_PASSWORD}),
  });
  assert.equal(auth.status,200);
  token = (await auth.json()).access_token;
}
assert.ok(token);
const me = await fetch(supabase+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token},redirect:'error'});
assert.equal(me.status,200);
assert.equal((await me.json()).id,'c003287a-10ce-4cc9-926e-ef7c3a162a26');
const headers={Origin:'https://staging.srnastudytool.com',Authorization:'Bearer '+token,'Content-Type':'application/json'};
const ids=['96a5610a-7ee0-48f1-acb9-07d4ceeebd58','8ec6f64c-9767-4a88-8d7f-8780ad3431c9','41eca576-e288-49a2-a54e-37ebd986dcb2'];
for (const id of ids) {
  const endpoint=gateway+'/generation/drafts/'+id;
  try {
    const before=await fetch(endpoint,{headers,redirect:'error',signal:AbortSignal.timeout(20000)});
    if(!before.ok){console.log(JSON.stringify({draft:id,read_http:before.status}));continue;}
    const draft=await before.json();
    if (draft.can_complete_option_review!==true || draft.published!==false) {
      const pending = Object.entries(draft.screening?.stages||{}).filter(([name,stage])=>name!=='human_review'&&stage.status!=='pass').map(([name])=>name);
      console.log(JSON.stringify({draft:id,eligible:false,status:draft.status,pending}));continue;
    }
    const response=await fetch(endpoint+'/complete-options',{method:'POST',headers,redirect:'error',
      signal:AbortSignal.timeout(105000),body:JSON.stringify({confirm_paid_calls:true,expected_updated_at:draft.updated_at})});
    const result=await response.json().catch(()=>null);
    if(!response.ok){console.log(JSON.stringify({draft:id,http:response.status}));continue;}
    assert.equal(result.published,false);assert.equal(result.generation_performed,false);assert.equal(result.question_modified,false);
    console.log(JSON.stringify({draft:id,option_review:result.option_review_status,all_checks_passed:result.automated_checks_passed,review_call:result.paid_review_performed}));
  } catch (error) {
    console.log(JSON.stringify({draft:id,transport:error.name}));
  }
}
