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
console.log('Unauthenticated live staging reviewer boundary acceptance passed');
