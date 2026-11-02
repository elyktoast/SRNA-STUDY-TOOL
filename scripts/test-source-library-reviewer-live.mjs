import assert from 'node:assert/strict';
const base=process.env.SRNA_REVIEWER_GATEWAY_URL;
if(!base)throw Error('SRNA_REVIEWER_GATEWAY_URL required for live acceptance');
const origin='https://staging.srnastudytool.com';
const root=new URL(base);
assert.equal(root.protocol,'https:');
assert.equal(root.pathname,'/');
assert.ok(root.hostname.endsWith('.srnastudytool.com') || root.hostname==='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev');
const request=async(path,init={})=>fetch(new URL(path,root),{redirect:'error',...init});
const tests=[
 ['/review/approve',{method:'POST',headers:{Origin:origin}},[403,404,405]],
 ['/review/manifest?path=invalid.pdf',{headers:{Origin:origin}},[401,403]],
 ['/review/page.png?path=invalid.pdf&page=1',{headers:{Origin:origin}},[401,403]],
 ['/review/manifest?path=invalid.pdf',{headers:{Origin:'https://example.com'}},[403]],
 ['/review/manifest?path=invalid.pdf',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'Authorization'}},[403]],
 ['/review/manifest?path=invalid.pdf',{method:'OPTIONS',headers:{Origin:origin,'Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'Authorization'}},[204]],
];
for(const [path,init,allowed] of tests){
 const response=await request(path,init);
 assert.ok(allowed.includes(response.status),path+': unexpected HTTP '+response.status);
 assert.equal(response.headers.get('X-Review-Approval-Enabled'),'false',path);
 assert.match(response.headers.get('Cache-Control')||'',/no-store/,path);
 console.log(path,response.status);
}
// Negative bearer tokens must never unlock private source data.
for (const authorization of ['Bearer invalid-token', 'Bearer malformed.invalid.token']) {
 const response=await request('/review/manifest?path=invalid.pdf',{headers:{Origin:origin,Authorization:authorization}});
 assert.ok([401,403,503].includes(response.status),'invalid bearer must not succeed: '+response.status);
 assert.equal(response.headers.get('X-Review-Approval-Enabled'),'false');
 assert.match(response.headers.get('Cache-Control')||'',/no-store/);
 console.log('Invalid bearer rejected:',response.status);
}

// Optional authenticated acceptance: only a dedicated GitHub Actions secret may
// supply a staging admin access token. Never log it or include it in URLs.
const authenticatedToken=process.env.SRNA_STAGING_REVIEWER_ACCESS_TOKEN;
const authenticatedPath=process.env.SRNA_STAGING_REVIEWER_PDF_KEY;
if(Boolean(authenticatedToken)!==Boolean(authenticatedPath)){
 throw Error('Both authenticated staging acceptance inputs must be configured together');
}
if(authenticatedToken){
 // Log only coarse JWT validity signals. Never expose claims, identifiers, or token bytes.
 let claims=null;
 try {
  const segments=authenticatedToken.split('.');
  if(segments.length===3)claims=JSON.parse(Buffer.from(segments[1],'base64url').toString('utf8'));
 } catch {}
 const now=Math.floor(Date.now()/1000);
 console.log('Staging credential diagnostics:',JSON.stringify({
  jwt_structure_valid:!!claims,
  issuer_matches_staging:claims?.iss==='https://xqyasyambwdyhsjkftqu.supabase.co/auth/v1',
  unexpired:Number.isFinite(claims?.exp)&&claims.exp>now,
  issued_in_past:Number.isFinite(claims?.iat)&&claims.iat<=now+60,
  bearer_has_no_whitespace:!(/\\s/.test(authenticatedToken))
 }));
 assert.match(authenticatedPath,/^[0-9a-f-]{36}\/[A-Za-z0-9._-]+\.pdf$/i);
 const headers={Origin:origin,Authorization:'Bearer '+authenticatedToken};
 const manifestResponse=await request('/review/manifest?path='+encodeURIComponent(authenticatedPath),{headers});
 assert.equal(manifestResponse.status,200,'authenticated manifest: HTTP '+manifestResponse.status);
 const manifest=await manifestResponse.json();
 assert.match(manifest.source_sha256,/^[0-9a-f]{64}$/);
 assert.ok(Number.isSafeInteger(manifest.pdf_page_count)&&manifest.pdf_page_count>=1);
 assert.equal(manifest.approval_enabled,false);
 assert.equal(manifestResponse.headers.get('X-Verified-Source-SHA256'),manifest.source_sha256);
 const pageResponse=await request('/review/page.png?path='+encodeURIComponent(authenticatedPath)+'&page=1',{headers});
 assert.equal(pageResponse.status,200,'authenticated PNG: HTTP '+pageResponse.status);
 assert.match(pageResponse.headers.get('content-type')||'',/^image\/png/i);
 assert.equal(pageResponse.headers.get('X-Verified-Source-SHA256'),manifest.source_sha256);
 assert.match(pageResponse.headers.get('X-Page-Image-SHA256')||'',/^[0-9a-f]{64}$/);
 assert.equal(pageResponse.headers.get('X-Review-Approval-Enabled'),'false');
 const image=new Uint8Array(await pageResponse.arrayBuffer());
 assert.ok(image.length>=8 && [137,80,78,71,13,10,26,10].every((b,i)=>image[i]===b));
 const actualHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',image)),b=>b.toString(16).padStart(2,'0')).join('');
 assert.equal(actualHash,pageResponse.headers.get('X-Page-Image-SHA256'));
 console.log('PASS: authenticated staging reviewer manifest and verified PDF page PNG');
}

console.log('Live staging reviewer boundary acceptance passed');
