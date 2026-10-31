import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
const source=readFileSync(new URL('../workers/source-library-staging/src/index.js',import.meta.url),'utf8');
const worker=(await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'))).default;
const origin='https://staging.srnastudytool.com';
const uid='123e4567-e89b-42d3-a456-426614174000';
const objects=new Map();
const env={STAGING_ONLY:'true',ALLOWED_ORIGIN:origin,SUPABASE_URL:'https://staging-auth.example',SUPABASE_ANON_KEY:'test-public-key',ADMIN_USER_IDS:uid,TEXTBOOKS:{
 async list({prefix}){return {objects:[...objects].filter(([key])=>key.startsWith(prefix)).map(([key,v])=>({key,size:v.length,uploaded:new Date(),customMetadata:{name:'test.pdf'}})),truncated:false}},
 async put(key,body){objects.set(key,typeof body==='string'?new TextEncoder().encode(body):new Uint8Array(body))},
 async get(key){const v=objects.get(key);return v?{body:v,text:async()=>new TextDecoder().decode(v)}:null},
 async head(key){return objects.has(key)?{key}:null},
 async delete(key){objects.delete(key)}
}};
const previousFetch=globalThis.fetch;
const authCalls=[];
globalThis.fetch=async (url,options)=>{authCalls.push(String(url));return new Response(options?.headers?.authorization==='Bearer valid'?JSON.stringify({id:uid}):options?.headers?.authorization==='Bearer anonymous'?JSON.stringify({id:uid,is_anonymous:true}):'{}',{status:['Bearer valid','Bearer anonymous'].includes(options?.headers?.authorization)?200:401,headers:{'content-type':'application/json'}})};
function request(path,method='GET',headers={},body){return worker.fetch(new Request('https://staging-worker.example'+path,{method,headers:{origin,authorization:'Bearer valid',...headers},body}),env)}
test('rejects foreign origins',async()=>{const r=await worker.fetch(new Request('https://staging-worker.example/materials',{headers:{origin:'https://srnastudytool.com'}}),env);assert.equal(r.status,403)});
test('requires authentication',async()=>{const r=await request('/materials','GET',{authorization:'Bearer invalid'});assert.equal(r.status,403)});
test('rejects a non-allowlisted token through configured Supabase identity endpoint',async()=>{
 const before=authCalls.length;
 const r=await request('/materials','GET',{authorization:'Bearer unrelated-token'});
 assert.equal(r.status,403);
 assert.deepEqual(authCalls.slice(before),['https://staging-auth.example/auth/v1/user']);
});
test('rejects anonymous identity even if allowlisted',async()=>{const r=await request('/materials','GET',{authorization:'Bearer anonymous'});assert.equal(r.status,403)});
test('requires admin allowlist',async()=>{const r=await worker.fetch(new Request('https://staging-worker.example/materials',{headers:{origin,authorization:'Bearer valid'}}),{...env,ADMIN_USER_IDS:'00000000-0000-4000-8000-000000000000'});assert.equal(r.status,403)});
test('accepts additional staging admin without removing original admin',async()=>{
 const second='c003287a-10ce-4cc9-926e-ef7c3a162a26';
 const old=globalThis.fetch;
 globalThis.fetch=async()=>new Response(JSON.stringify({id:second}),{status:200,headers:{'content-type':'application/json'}});
 try {
  const r=await worker.fetch(new Request('https://staging-worker.example/materials',{headers:{origin,authorization:'Bearer valid'}}),{...env,ADDITIONAL_ADMIN_USER_IDS:second});
  assert.equal(r.status,200);
 } finally {globalThis.fetch=old;}
});
test('rejects non-PDF upload',async()=>{const r=await request('/materials','POST',{'content-type':'application/pdf'},'not a pdf');assert.equal(r.status,415)});
test('rejects oversized upload',async()=>{const r=await request('/materials','POST',{'content-type':'application/pdf'},'%PDF-'+'.'.repeat(20*1024*1024));assert.equal(r.status,413)});
test('uploads, lists, downloads and deletes user-owned PDF',async()=>{
 const upload=await request('/materials','POST',{'content-type':'application/pdf','x-file-name':'test.pdf'},'%PDF-1.4\nhello');
 assert.equal(upload.status,201);const result=await upload.json();assert.ok(result.path.startsWith(uid+'/'));
 const list=await request('/materials');assert.equal((await list.json()).items.length,1);
 const file=await request('/materials/item?path='+encodeURIComponent(result.path));assert.equal(file.status,200);assert.match(await file.text(),/^%PDF-/);
 const other=await request('/materials/item?path=00000000-0000-4000-8000-000000000000%2Ffoo.pdf');assert.equal(other.status,400);
 const deleted=await request('/materials/item?path='+encodeURIComponent(result.path),'DELETE');assert.equal(deleted.status,200);
 const missing=await request('/materials/item?path='+encodeURIComponent(result.path));assert.equal(missing.status,404);
});
test('fails closed when staging configuration is missing',async()=>{const r=await worker.fetch(new Request('https://staging-worker.example/materials',{headers:{origin}}),{...env,TEXTBOOKS:undefined});assert.equal(r.status,503)});
test.after(()=>{globalThis.fetch=previousFetch});

test('saves, loads and deletes an unapproved owner-scoped review draft',async()=>{
 const pdf=uid+'/chapter-review-test.pdf';
 objects.set(pdf,new TextEncoder().encode('%PDF-1.4'));
 const path='/chapter-reviews/draft?path='+encodeURIComponent(pdf);
 const payload={schema_version:2,review_fingerprint:'a'.repeat(64),decisions:[{group:1,decision:'Chapter',notes:'reviewed'}]};
 const saved=await request(path,'PUT',{'content-type':'application/json'},JSON.stringify(payload));
 assert.equal(saved.status,200);
 assert.equal((await saved.json()).approved,false);
 const loaded=await request(path);
 assert.equal(loaded.status,200);
 assert.deepEqual(await loaded.json(),payload);
 const listed=await request('/materials');
 assert.ok(!(await listed.json()).items.some(x=>x.path.includes('_review_drafts')));
 const removed=await request(path,'DELETE');
 assert.equal(removed.status,200);
 assert.equal((await request(path)).status,404);
 objects.delete(pdf);
});
test('rejects foreign owner and invalid review drafts',async()=>{
 const pdf=uid+'/invalid-review-test.pdf';objects.set(pdf,new TextEncoder().encode('%PDF-1.4'));
 const foreign=await request('/chapter-reviews/draft?path=00000000-0000-4000-8000-000000000000%2Ffile.pdf','PUT',{},'{}');
 assert.equal(foreign.status,400);
 const invalid=await request('/chapter-reviews/draft?path='+encodeURIComponent(pdf),'PUT',{'content-type':'application/json'},JSON.stringify({schema_version:2,review_fingerprint:'a'.repeat(64),decisions:[{group:2,decision:'Chapter',notes:''}]}));
 assert.equal(invalid.status,400);
 objects.delete(pdf);
});

test('rejects oversized streamed review draft without saving',async()=>{
 const pdf=uid+'/oversized-review-test.pdf';objects.set(pdf,new TextEncoder().encode('%PDF-1.4'));
 const path='/chapter-reviews/draft?path='+encodeURIComponent(pdf);
 const before=objects.size;
 const response=await request(path,'PUT',{'content-type':'application/json'},' '.repeat(256*1024+1));
 assert.equal(response.status,413);
 assert.equal(objects.size,before);
 objects.delete(pdf);
});
test('rejects invalid UTF-8 review draft with a client error',async()=>{
 const pdf=uid+'/invalid-encoding-test.pdf';objects.set(pdf,new TextEncoder().encode('%PDF-1.4'));
 const response=await request('/chapter-reviews/draft?path='+encodeURIComponent(pdf),'PUT',{'content-type':'application/json'},new Uint8Array([0xff,0xfe]));
 assert.equal(response.status,400);
 objects.delete(pdf);
});
