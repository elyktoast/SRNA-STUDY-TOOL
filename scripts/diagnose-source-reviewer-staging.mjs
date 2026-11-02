import assert from 'node:assert/strict';
const token=process.env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
const key=process.env.STAGING_SUPABASE_ANON_KEY;
const pdf=process.env.SRNA_STAGING_REVIEWER_PDF_KEY;
const gateway='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
const project='https://xqyasyambwdyhsjkftqu.supabase.co';
const origin='https://staging.srnastudytool.com';
function check(value,name){if(!value)throw Error(name+': missing secret or variable')}
for(const [v,n] of [[token,'admin token'],[key,'staging anon key'],[pdf,'test PDF']])check(v,n);
function jwt(value){try{return JSON.parse(Buffer.from(value.split('.')[1],'base64url').toString('utf8'))}catch{return null}}
const a=jwt(key),t=jwt(token);
assert.equal(a?.role,'anon','legacy anon key role mismatch');
assert.equal(a?.ref,'xqyasyambwdyhsjkftqu','legacy anon key project mismatch');
assert.equal(t?.iss,project+'/auth/v1','admin token issuer mismatch');
assert.ok(t.exp>Math.floor(Date.now()/1000),'admin token expired');
console.log('STEP 1: staging credentials: valid structure and project');
// Staging-only automated verification can run on branch pushes before this workflow exists on main.
// Fetch the identity endpoint without logging any credential or server response.
const id=await fetch(project+'/auth/v1/user',{headers:{apikey:key,Authorization:'Bearer '+token},redirect:'manual'});
console.log('STEP 2: direct Supabase identity: HTTP',id.status);
assert.equal(id.status,200,'direct Supabase identity failed; stop before Container');
const user=await id.json();
assert.ok(user?.id&&!user.is_anonymous,'identity must be an authenticated user');
const headers={Origin:origin,Authorization:'Bearer '+token};
const negative=await fetch(gateway+'/review/manifest?path=invalid.pdf',{headers:{Origin:origin}});
console.log('STEP 3: unauthenticated gateway boundary: HTTP',negative.status);
assert.equal(negative.status,401);
const url=gateway+'/review/manifest?path='+encodeURIComponent(pdf);
const manifestResponse=await fetch(url,{headers,redirect:'manual'});
let safeError='none';
if(manifestResponse.status!==200){
 const body=await manifestResponse.json().catch(()=>null);
 const allowed=new Set(['identity_unavailable','reviewer_unavailable','staging_not_configured','forbidden','unsafe_upstream','invalid_manifest','missing_source_integrity','manifest_integrity_mismatch','invalid_manifest_type','reviewer_backend_unavailable']);
 safeError=allowed.has(body?.error)?body.error:'unclassified';
 if(body?.error==='reviewer_backend_unavailable' && ['configuration','database','dependency','backend'].includes(body?.stage)) safeError+=':'+body.stage;
}
console.log('STEP 4: authenticated Container -> manifest: HTTP',manifestResponse.status,'category',safeError);
assert.equal(manifestResponse.status,200,'Container/manifest failed: inspect staging_reviewer_failure substage in Cloudflare');
const manifest=await manifestResponse.json();
assert.match(manifest.source_sha256,/^[a-f0-9]{64}$/);
assert.ok(Number.isInteger(manifest.pdf_page_count)&&manifest.pdf_page_count>0);
console.log('STEP 5: manifest integrity: passed, page count',manifest.pdf_page_count);
const pageResponse=await fetch(gateway+'/review/page.png?path='+encodeURIComponent(pdf)+'&page=1',{headers,redirect:'manual'});
console.log('STEP 6: first-page PNG: HTTP',pageResponse.status);
assert.equal(pageResponse.status,200);
assert.match(pageResponse.headers.get('Content-Type')||'',/^image\/png/i);
const bytes=new Uint8Array(await pageResponse.arrayBuffer());
assert.ok([137,80,78,71,13,10,26,10].every((b,i)=>bytes[i]===b),'PNG signature invalid');
const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
assert.equal(hash,pageResponse.headers.get('X-Page-Image-SHA256'),'PNG digest mismatch');
assert.equal(pageResponse.headers.get('X-Verified-Source-SHA256'),manifest.source_sha256,'PDF digest mismatch');
console.log('STEP 7: PDF and page SHA256 integrity: passed');

const preflightOptions=await fetch(gateway+'/generation/preflight',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'authorization,content-type'},redirect:'manual'});
console.log('STEP 8: generation CORS preflight: HTTP',preflightOptions.status);
assert.equal(preflightOptions.status,204,'generation CORS route unavailable');
const anonymousGeneration=await fetch(gateway+'/generation/preflight',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:'{}',redirect:'manual'});
console.log('STEP 9: unauthenticated generation boundary: HTTP',anonymousGeneration.status);
assert.equal(anonymousGeneration.status,401,'generation endpoint must reject anonymous callers');
const evidenceResponse=await fetch(gateway+'/generation/preflight',{method:'POST',headers:{...headers,'Content-Type':'application/json'},body:JSON.stringify({topic:'airway',mode:'NCE',domain:'unassigned',section:'unassigned',objective:'Evidence availability only',item_id:'preflight',format:'MC'}),redirect:'manual'});
const evidence=await evidenceResponse.json().catch(()=>null);
const evidenceStatus=evidenceResponse.status===200?'indexed_evidence_found':evidenceResponse.status===422&&evidence?.error==='no_indexed_evidence'?'no_indexed_evidence':'unexpected_response';
console.log('STEP 10: authenticated generation preflight: HTTP',evidenceResponse.status,'category',evidenceStatus);
assert.ok(evidenceStatus!=='unexpected_response','generation preflight failed or service unavailable');
if(evidenceResponse.status===200){
 assert.equal(evidence?.dry_run,true);
 assert.equal(evidence?.can_publish,false);
 assert.equal(evidence?.database_writes,false);
 assert.ok(Number.isSafeInteger(evidence?.passage_count)&&evidence.passage_count>0);
}
