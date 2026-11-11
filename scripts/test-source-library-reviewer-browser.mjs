import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';
import {fileURLToPath} from 'node:url';
import {webcrypto} from 'node:crypto';

const source=readFileSync(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url),'utf8');
const origin='https://staging.srnastudytool.com';
const reviewer='https://reviewer-staging.srnastudytool.com';
const pdf='123e4567-e89b-42d3-a456-426614174000/book.pdf';
const sha=async bytes=>Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex');

function preview(question){
 const ui=readFileSync(new URL('../equipment/assets/source-library-staging-ui.js',import.meta.url),'utf8');
 const node=tag=>({tag,children:[],textContent:'',append(child){this.children.push(child)},replaceChildren(){this.children=[]},set innerHTML(value){throw Error('Generated content must be text')}});
 const document={createElement:node},host=node('div');
 const render=vm.runInNewContext(ui.slice(ui.indexOf('function renderReadableQuestion('),ui.indexOf('let generatedForReview='))+'\nrenderReadableQuestion',{document});
 render(host,question);
 const text=n=>[n.textContent,...n.children.map(text)].join('\n');return text(host);
}
test('saved v2 question preview exposes the four-part teaching rationale and PDF citations safely',()=>{
 const html='<img src=x onerror=alert(1)>';
 const text=preview({stem:'Clinical case',mode:'NCE',objective:'I.A.2',reasoning_level:'application',key:['B'],options:[{id:'A',text:'First response'},{id:'B',text:'Second response'}],
  rationale:{core_concept:'Core teaching',why_key_wins:'Key mechanism',trap:html,distractor_breakdown:{A:'Specific wrong mechanism',B:'Duplicate keyed breakdown'}},evidence:[{pdf_page:731},{pdf_page:732}]});
 for(const value of ['Core teaching','Key mechanism',html,'Specific wrong mechanism','I.A.2','731, 732','Clinical review required'])assert.ok(text.includes(value),value);
 assert.ok(!text.includes('Duplicate keyed breakdown'));
});
test('legacy string rationale remains readable',()=>{
 assert.ok(preview({stem:'Legacy case',explanation:'Legacy teaching'}).includes('Legacy teaching'));
});

function setup({hostname='staging.srnastudytool.com',reviewerApiUrl=reviewer,handler}={}){
 const calls=[];
 const context={
  window:{MBU_SOURCE_LIBRARY_STAGING:{enabled:true,apiUrl:'https://source-library-staging.srnastudytool.com',reviewerApiUrl}},
  location:{hostname},URL,Blob,crypto:webcrypto,
  localStorage:{getItem:()=>JSON.stringify({access_token:'staging-jwt'})},
  fetch:async(url,options)=>{calls.push({url:String(url),options});return handler(url,options)}
 };
 context.globalThis=context;
 vm.runInNewContext(source,context,{filename:fileURLToPath(new URL('../equipment/assets/source-material-staging-storage.js',import.meta.url)),importModuleDynamically:vm.constants.USE_MAIN_CONTEXT_DEFAULT_LOADER});
 return {api:context.window.MBUSourceMaterialStagingStorage,calls};
}
function response(bytes,sourceSha,imageSha,{mime='image/png',approval='false'}={}){
 return new Response(new Blob([bytes],{type:mime}),{headers:{
  'Content-Type':mime,'X-Review-Approval-Enabled':approval,
  'X-Verified-Source-SHA256':sourceSha,'X-Page-Image-SHA256':imageSha
 }});
}
const png=new Uint8Array([137,80,78,71,13,10,26,10,0,0,0,0]);

test('verified browser preview hashes the actual PNG and keeps request private',async()=>{
 const digest=await sha(png),sourceSha='a'.repeat(64);
 const {api,calls}=setup({handler:()=>response(png,sourceSha,digest)});
 const result=await api.verifiedReviewPage(pdf,1);
 assert.equal(result.imageSha256,digest);
 assert.equal(result.sourceSha256,sourceSha);
 assert.equal(result.approvalEnabled,false);
 assert.equal(calls.length,1);
 assert.equal(calls[0].url,reviewer+'/review/page.png?path='+encodeURIComponent(pdf)+'&page=1');
 assert.equal(calls[0].options.headers.Authorization,'Bearer staging-jwt');
 assert.equal(calls[0].options.credentials,'omit');
 assert.equal(calls[0].options.cache,'no-store');
 assert.equal(calls[0].options.redirect,'error');
});
test('browser rejects a forged PNG fingerprint',async()=>{
 const {api}=setup({handler:()=>response(png,'a'.repeat(64),'0'.repeat(64))});
 await assert.rejects(api.verifiedReviewPage(pdf,1),/fingerprint mismatch/);
});
test('browser rejects missing approval guard and non-PNG payload',async()=>{
 for(const options of [{approval:'true'},{mime:'text/plain'}]){
  const {api}=setup({handler:()=>response(png,'a'.repeat(64),'0'.repeat(64),options)});
  await assert.rejects(api.verifiedReviewPage(pdf,1));
 }
});
test('browser refuses production, lookalike, and insecure reviewer URLs',async()=>{
 for(const reviewerApiUrl of [
  'http://reviewer-staging.srnastudytool.com',
  'https://srnastudytool.com',
  'https://staging.srnastudytool.com',
  'https://reviewer-staging.srnastudytool.com.evil.test'
 ]){
  const {api,calls}=setup({reviewerApiUrl,handler:()=>{throw Error('Should not fetch')}});
  await assert.rejects(api.verifiedReviewPage(pdf,1),/not configured/);
  assert.equal(calls.length,0);
 }
});
test('browser validates physical page number before fetching',async()=>{
 const {api,calls}=setup({handler:()=>{throw Error('Should not fetch')}});
 await assert.rejects(api.verifiedReviewPage(pdf,0),/Invalid physical PDF page/);
 assert.equal(calls.length,0);
});

test('mobile acceptance reuses session and verifies real page bytes without exporting token',async()=>{
 const sourceSha='b'.repeat(64),digest=await sha(png);
 const {api,calls}=setup({handler:(url)=>{
  if(String(url).includes('/review/manifest?'))return new Response(JSON.stringify({
   source_sha256:sourceSha,pdf_page_count:2,approval_enabled:false
  }),{headers:{'Content-Type':'application/json','X-Review-Approval-Enabled':'false',
   'X-Verified-Source-SHA256':sourceSha}});
  return response(png,sourceSha,digest);
 }});
 const result=await api.mobileReviewerAcceptance(pdf);
 assert.equal(result.verified,true);
 assert.equal(result.pdfPages,2);
 assert.equal(calls.length,2);
 for(const call of calls){
  assert.ok(call.url.startsWith('https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/review/'));
  assert.equal(call.options.headers.Authorization,'Bearer staging-jwt');
  assert.equal(call.options.credentials,'omit');
  assert.equal(call.options.cache,'no-store');
  assert.equal(call.options.redirect,'error');
 }
});
test('mobile acceptance rejects forged page fingerprints and wrong host',async()=>{
 const sourceSha='b'.repeat(64);
 const {api}=setup({handler:url=>String(url).includes('/review/manifest?')?
  new Response(JSON.stringify({source_sha256:sourceSha,pdf_page_count:1,approval_enabled:false}),{
   headers:{'X-Review-Approval-Enabled':'false','X-Verified-Source-SHA256':sourceSha}
  }):response(png,sourceSha,'0'.repeat(64))});
 await assert.rejects(api.mobileReviewerAcceptance(pdf),/integrity verification failed/);
 const foreign=setup({hostname:'srnastudytool.com',handler:()=>{throw Error('Must not fetch')}});
 await assert.rejects(foreign.api.mobileReviewerAcceptance(pdf),/Staging-only/);
 assert.equal(foreign.calls.length,0);
});

test('mobile acceptance reports auth and gateway errors instead of misleading unsafe response',async()=>{
 for(const [status,error] of [[401,'authentication_required'],[403,'forbidden'],[502,'unsafe_upstream']]){
  const {api,calls}=setup({handler:()=>new Response(JSON.stringify({error}),{
   status,headers:{'Content-Type':'application/json'}
  })});
  await assert.rejects(api.mobileReviewerAcceptance(pdf),
   new RegExp('Reviewer acceptance HTTP '+status+' \\('+error+'\\)'));
  assert.equal(calls.length,1);
 }
});
test('mobile acceptance rejects successful response without disabled-approval header',async()=>{
 const {api}=setup({handler:()=>new Response('{}',{status:200})});
 await assert.rejects(api.mobileReviewerAcceptance(pdf),/successful response missing disabled-approval header/);
});

test('evidence preflight sends staging bearer only to pinned reviewer gateway',async()=>{
 const endpoint='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/';
 // Expose the config to the test harness through a standalone VM.
 const captured=[];
 const ctx={window:{MBU_SOURCE_LIBRARY_STAGING:{enabled:true,apiUrl:'https://source-library-staging.srnastudytool.com',generationApiUrl:endpoint}},location:{hostname:'staging.srnastudytool.com'},URL,Blob,crypto:webcrypto,localStorage:{getItem:()=>JSON.stringify({access_token:'staging-jwt'})},fetch:async(url,options)=>{captured.push({url,options});return Response.json({dry_run:true,passage_count:2})}};
 vm.runInNewContext(source,ctx);
 const result=await ctx.window.MBUSourceMaterialStagingStorage.generationPreflight({topic:'airway'});
 assert.equal(result.passage_count,2);
 assert.equal(captured[0].url,endpoint+'generation/preflight');
 assert.equal(captured[0].options.headers.Authorization,'Bearer staging-jwt');
 assert.equal(captured[0].options.credentials,'omit');
 assert.equal(captured[0].options.redirect,'error');
 assert.equal(captured[0].options.cache,'no-store');
});
test('evidence preflight refuses arbitrary and production endpoints before network access',async()=>{
 for(const endpoint of ['https://evil.example/','https://srnastudytool.com/','http://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/']){
  let calls=0;
  const ctx={window:{MBU_SOURCE_LIBRARY_STAGING:{enabled:true,apiUrl:'https://source-library-staging.srnastudytool.com',generationApiUrl:endpoint}},location:{hostname:'staging.srnastudytool.com'},URL,Blob,crypto:webcrypto,localStorage:{getItem:()=>JSON.stringify({access_token:'staging-jwt'})},fetch:async()=>{calls++;throw Error('Unexpected network call')}};
  vm.runInNewContext(source,ctx);
  await assert.rejects(ctx.window.MBUSourceMaterialStagingStorage.generationPreflight({topic:'airway'}),/Invalid staging generation backend/);
  assert.equal(calls,0);
 }
});

test('staging evidence check defaults to pinned accepted gateway and permits explicit disable',async()=>{
 const endpoint='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/generation/preflight';
 for(const override of [undefined,null]){
  const captured=[];
  const cfg={enabled:true,apiUrl:'https://source-library-staging.srnastudytool.com'};
  if(override===null)cfg.generationApiUrl=null;
  const ctx={window:{MBU_SOURCE_LIBRARY_STAGING:cfg},location:{hostname:'staging.srnastudytool.com'},URL,Blob,crypto:webcrypto,localStorage:{getItem:()=>JSON.stringify({access_token:'staging-jwt'})},fetch:async(url)=>{captured.push(url);return Response.json({dry_run:true,passage_count:1})}};
  vm.runInNewContext(source,ctx);
  if(override===null){await assert.rejects(ctx.window.MBUSourceMaterialStagingStorage.generationPreflight({topic:'airway'}),/disabled/);assert.equal(captured.length,0)}
  else {await ctx.window.MBUSourceMaterialStagingStorage.generationPreflight({topic:'airway'});assert.equal(captured[0],endpoint)}
 }
});


test('saved draft detail uses authenticated staging GET without publishing',async()=>{
 const draft='abc90a93-41f8-4d7c-8e27-94a609135572';
 const {api,calls}=setup({handler:()=>new Response(JSON.stringify({draft_id:draft,status:'pending_review',published:false,question:{stem:'Test'}}),{status:200,headers:{'Content-Type':'application/json'}})});
 const data=await api.getGeneratedDraft(draft);
 assert.equal(data.published,false);
 assert.equal(data.status,'pending_review');
 assert.equal(calls.length,1);
 assert.equal(calls[0].url,'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/generation/drafts/'+draft);
 assert.equal(calls[0].options.headers.Authorization,'Bearer staging-jwt');
 assert.equal(calls[0].options.credentials,'omit');
 assert.equal(calls[0].options.cache,'no-store');
 assert.equal(calls[0].options.redirect,'error');
 assert.equal(calls[0].options.method,undefined);
});
test('saved draft detail rejects invalid IDs and non-staging origin before fetch',async()=>{
 const draft='abc90a93-41f8-4d7c-8e27-94a609135572';
 const {api,calls}=setup({handler:()=>{throw Error('unexpected network request')}});
 await assert.rejects(api.getGeneratedDraft('../drafts'),/Invalid draft ID/);
 assert.equal(calls.length,0);
 const outside=setup({hostname:'srnastudytool.com',handler:()=>{throw Error('unexpected network request')}});
 await assert.rejects(outside.api.getGeneratedDraft(draft),/Staging only/);
 assert.equal(outside.calls.length,0);
});
test('saved draft detail surfaces backend failures',async()=>{
 const {api}=setup({handler:()=>new Response(JSON.stringify({error:'Draft not found'}),{status:404,headers:{'Content-Type':'application/json'}})});
 await assert.rejects(api.getGeneratedDraft('abc90a93-41f8-4d7c-8e27-94a609135572'),/Draft not found/);
});


test('disconnected generation retrieves only the same completed request without new authoring',async()=>{
 const request={item_id:'stable-id',topic:'original topic',textbook_id:'owned-book'};let networkCalls=0,recoveryNotice=0;
 const {api,calls}=setup({handler:async(url,options)=>{
  const body=JSON.parse(options.body);
  if(++networkCalls===1){assert.equal(body.resume_completed_only,undefined);throw TypeError('fetch failed');}
  assert.deepEqual(body,{...request,resume_completed_only:true});
  return {ok:true,json:async()=>({draft_id:'saved-id',published:false,can_publish:false})};
 }});
 const result=await api.generateOne(request,{onRecovery:()=>recoveryNotice++});
 assert.equal(result.draft_id,'saved-id');assert.equal(result.published,false);
 assert.equal(calls.length,2);assert.equal(recoveryNotice,1);assert.equal(request.resume_completed_only,undefined);
});
