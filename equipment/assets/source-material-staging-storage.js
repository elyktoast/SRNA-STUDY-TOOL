(()=>{'use strict';
// Staging-only adapter. Not loaded by production unless explicitly included in a staging build.
const config=window.MBU_SOURCE_LIBRARY_STAGING||{};
const sessionKey='mbu_supabase_session_v1';
function settings(){const base=String(config.apiUrl||'').replace(/\/$/,'');let url;try{url=new URL(base)}catch{}if(location.hostname!=='staging.srnastudytool.com'||!config.enabled||!url||url.protocol!=='https:'||url.username||url.password||url.search||url.hash||url.pathname!=='/'||url.hostname==='srnastudytool.com'||url.hostname==='www.srnastudytool.com')throw Error('Staging Source Library is not configured.');return url.origin;}
function token(){let s;try{s=JSON.parse(localStorage.getItem(sessionKey)||'null')}catch{}const jwt=s?.access_token;if(!jwt)throw Error('Sign in to the staging account first.');return jwt;}
async function call(path,options={}){
 const response=await fetch(settings()+path,{...options,headers:{Authorization:'Bearer '+token(),...(options.headers||{})}});
 if(!response.ok){const error=await response.json().catch(()=>null);throw Error(error?.error||'Staging storage request failed ('+response.status+').')}
 return response;
}
function key(path){if(typeof path!=='string'||!path||path.includes('..')||path.includes('\\')||path.startsWith('/'))throw Error('Invalid source material path.');return encodeURIComponent(path)}
async function save(file){
 if(!(file instanceof File))throw Error('Choose a PDF file.');
 if(file.type&&file.type!=='application/pdf'||!file.name.toLowerCase().endsWith('.pdf'))throw Error('Only PDF files are supported in staging.');
 if(file.size>300*1024*1024)throw Error('Staging PDF limit is 300 MiB.');
 if(file.size<=20*1024*1024){const response=await call('/materials',{method:'POST',headers:{'content-type':'application/pdf','x-file-name':file.name},body:file});return response.json();}
 const started=await call('/materials/multipart/start',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({name:file.name,size:file.size})}).then(r=>r.json());
 const params='path='+encodeURIComponent(started.path)+'&uploadId='+encodeURIComponent(started.uploadId);
 const parts=[];
 try{
  for(let offset=0,n=1;offset<file.size;offset+=started.partSize,n++){
   const chunk=file.slice(offset,Math.min(offset+started.partSize,file.size));
   const response=await call('/materials/multipart/part?'+params+'&part='+n,{method:'PUT',headers:{'content-type':'application/octet-stream'},body:chunk});
   parts.push(await response.json());
  }
  await call('/materials/multipart/complete?'+params,{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({parts})});
  return {path:started.path,name:file.name,size:file.size};
 }catch(e){try{await call('/materials/multipart/abort?'+params,{method:'DELETE'})}catch{}throw e;}
}
async function list(){const response=await call('/materials');const data=await response.json();return (data.items||[]).map(x=>({...x,createdAt:x.createdAt||x.savedAt}));}
async function file(path,name){const response=await call('/materials/item?path='+key(path));const blob=await response.blob();return new File([blob],name||'source-material.pdf',{type:'application/pdf'});}
async function download(path,name){const response=await call('/materials/item?path='+key(path));const blob=await response.blob();const url=URL.createObjectURL(blob);try{const a=document.createElement('a');a.href=url;a.download=name||'source-material.pdf';a.click()}finally{setTimeout(()=>URL.revokeObjectURL(url),1000)}}
async function reviewQueue(path){const response=await call('/materials/review-queue?path='+key(path));return response.json();}
async function reviewPdf(path){const response=await call('/materials/review-pdf?path='+key(path));const blob=await response.blob();if(blob.type!=='application/pdf')throw Error('Review endpoint did not return a PDF.');return blob;}
function reviewerSettings(){
 const base=String(config.reviewerApiUrl||'');let url;
 try{url=new URL(base)}catch{}
 if(location.hostname!=='staging.srnastudytool.com'||!config.enabled||!url||
    url.protocol!=='https:'||url.username||url.password||url.search||url.hash||
    url.pathname!=='/'||!url.hostname.endsWith('.srnastudytool.com')||
    url.hostname==='srnastudytool.com'||url.hostname==='www.srnastudytool.com'||
    url.hostname==='staging.srnastudytool.com')
   throw Error('Verified reviewer service is not configured for staging.');
 return url.origin;
}
async function reviewerCall(path){
 const response=await fetch(reviewerSettings()+path,{
  method:'GET',headers:{Authorization:'Bearer '+token()},cache:'no-store',
  credentials:'omit',redirect:'error'
 });
 if(!response.ok)throw Error('Verified reviewer request failed ('+response.status+').');
 if(response.headers.get('X-Review-Approval-Enabled')!=='false')
  throw Error('Unexpected reviewer approval state.');
 return response;
}
async function verifiedReviewManifest(path){
 const response=await reviewerCall('/review/manifest?path='+key(path));
 const data=await response.json();
 if(!/^[a-f0-9]{64}$/.test(data.source_sha256||'')||
    !Number.isSafeInteger(data.pdf_page_count)||data.pdf_page_count<1||
    data.approval_enabled!==false)
  throw Error('Invalid verified reviewer manifest.');
 return data;
}
async function verifiedReviewPage(path,page){
 if(!Number.isSafeInteger(page)||page<1)throw Error('Invalid physical PDF page.');
 const response=await reviewerCall('/review/page.png?path='+key(path)+'&page='+page);
 if(response.headers.get('Content-Type')!=='image/png')throw Error('Invalid reviewer page image.');
 const source=response.headers.get('X-Verified-Source-SHA256');
 const digest=response.headers.get('X-Page-Image-SHA256');
 if(!/^[a-f0-9]{64}$/.test(source||'')||!/^[a-f0-9]{64}$/.test(digest||''))
  throw Error('Missing verified page fingerprints.');
 const blob=await response.blob();
 if(blob.type!=='image/png')throw Error('Invalid image payload type.');
 if(blob.size===0||blob.size>32*1024*1024)throw Error('Invalid reviewer image size.');
 if(!globalThis.crypto?.subtle)throw Error('Browser SHA-256 verification unavailable.');
 const bytes=await blob.arrayBuffer();
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
 if(hash!==digest)throw Error('Reviewer image fingerprint mismatch.');
 return {blob,sourceSha256:source,imageSha256:digest,approvalEnabled:false};
}
// Staging-only read-only mobile acceptance. Reuses the current signed-in session
// in memory; it never displays, exports, persists or logs the bearer token.
// The gateway hostname is pinned, not supplied by a user or browser query.
async function mobileReviewerAcceptance(path){
 if(location.hostname!=='staging.srnastudytool.com'||!config.enabled)
  throw Error('Staging-only reviewer acceptance.');
 const endpoint='https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev';
 const auth='Bearer '+token();
 const request=async(route)=>{
  const response=await fetch(endpoint+route,{method:'GET',
   headers:{Authorization:auth},cache:'no-store',credentials:'omit',redirect:'error'});
  // Error responses may omit the approval header (e.g. gateway auth rejection).
  // Surface the HTTP failure first, without ever treating it as a verified page.
  if(!response.ok){
   const errorBody=await response.json().catch(()=>null);
   const reason=typeof errorBody?.error==='string'&&/^[a-z_]{1,64}$/.test(errorBody.error)
    ?' ('+errorBody.error+')':'';
   throw Error('Reviewer acceptance HTTP '+response.status+reason+
    (response.status===409?' — PDF review queue may be unpublished or source changed':
     response.status===401||response.status===403?' — check staging admin authorization':''));
  }
  if(response.headers.get('X-Review-Approval-Enabled')!=='false')
   throw Error('Unsafe reviewer response: successful response missing disabled-approval header.');
  return response;
 };
 const manifestResponse=await request('/review/manifest?path='+key(path));
 const manifest=await manifestResponse.json();
 if(!/^[a-f0-9]{64}$/.test(manifest.source_sha256||'')||
    !Number.isSafeInteger(manifest.pdf_page_count)||manifest.pdf_page_count<1||
    manifest.approval_enabled!==false||
    manifestResponse.headers.get('X-Verified-Source-SHA256')!==manifest.source_sha256)
  throw Error('Manifest source identity verification failed.');
 const pageResponse=await request('/review/page.png?path='+key(path)+'&page=1');
 if(pageResponse.headers.get('Content-Type')!=='image/png'||
    pageResponse.headers.get('X-Verified-Source-SHA256')!==manifest.source_sha256)
  throw Error('PDF page source verification failed.');
 const expected=pageResponse.headers.get('X-Page-Image-SHA256')||'';
 if(!/^[a-f0-9]{64}$/.test(expected))throw Error('Missing PNG SHA-256.');
 const data=await pageResponse.arrayBuffer();
 if(data.byteLength<8||data.byteLength>32*1024*1024)throw Error('Invalid PNG size.');
 const bytes=new Uint8Array(data);
 if(![137,80,78,71,13,10,26,10].every((b,i)=>bytes[i]===b))
  throw Error('Invalid PNG signature.');
 if(!crypto?.subtle)throw Error('SHA-256 unavailable in this browser.');
 const actual=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',data)),
  b=>b.toString(16).padStart(2,'0')).join('');
 if(actual!==expected)throw Error('PNG integrity verification failed.');
 return {pdfPages:manifest.pdf_page_count,verified:true};
}
async function remove(path){await call('/materials/item?path='+key(path),{method:'DELETE'});}
async function saveReviewDraft(path,draft){const response=await call('/chapter-reviews/draft?path='+key(path),{method:'PUT',headers:{'content-type':'application/json'},body:JSON.stringify(draft)});return response.json();}
async function loadReviewDraft(path){const response=await call('/chapter-reviews/draft?path='+key(path));return response.json();}
async function deleteReviewDraft(path){const response=await call('/chapter-reviews/draft?path='+key(path),{method:'DELETE'});return response.json();}
async function generationPreflight(request){const cfg=window.MBU_SOURCE_LIBRARY_STAGING||{};const raw=cfg.generationApiUrl===undefined?'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/':cfg.generationApiUrl;if(!raw||!cfg.enabled)throw Error('Generation preflight is disabled on staging.');const u=new URL(raw);if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.hostname!=='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev')throw Error('Invalid staging generation backend.');if(location.hostname!=='staging.srnastudytool.com')throw Error('Staging only.');const response=await fetch(u.origin+'/generation/preflight',{method:'POST',headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json'},credentials:'omit',cache:'no-store',redirect:'error',body:JSON.stringify(request)});const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.error||'Generation evidence preflight failed ('+response.status+').');return data;}
async function generationRequest(path,request){
 const cfg=window.MBU_SOURCE_LIBRARY_STAGING||{};
 if(location.hostname!=='staging.srnastudytool.com'||!cfg.enabled)throw Error('Staging only.');
 const raw=cfg.generationApiUrl===undefined?'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/':cfg.generationApiUrl;
 if(!raw)throw Error('Staging generation backend disabled.');
 const u=new URL(raw);
 if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.hostname!=='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev')throw Error('Invalid staging generation backend.');
 const response=await fetch(u.origin+path,{method:'POST',headers:{Authorization:'Bearer '+token(),'Content-Type':'application/json'},credentials:'omit',cache:'no-store',redirect:'error',body:JSON.stringify(request)});
 const data=await response.json().catch(()=>({}));
 if(!response.ok){const safeRule=typeof data.rule==='string'&&/^[A-Z][A-Z0-9_]{2,64}$/.test(data.rule)?' ['+data.rule+']':'';throw Error((data.error||'Staging generation request failed ('+response.status+').')+safeRule);}
 return data;
}
async function checkGroqConnection(){
 const cfg=window.MBU_SOURCE_LIBRARY_STAGING||{};
 const raw=cfg.generationApiUrl===undefined?'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/':cfg.generationApiUrl;
 if(!raw||!cfg.enabled||location.hostname!=='staging.srnastudytool.com')throw Error('Staging generation is disabled.');
 const u=new URL(raw);
 if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.hostname!=='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev')throw Error('Invalid staging generation backend.');
 const response=await fetch(u.origin+'/generation/provider-check',{method:'GET',headers:{Authorization:'Bearer '+token()},credentials:'omit',cache:'no-store',redirect:'error'});
 const data=await response.json().catch(()=>({}));
 if(!response.ok)throw Error((typeof data.rule==='string'?data.rule+': ':'')+(data.error||'Groq diagnostic failed')+' ('+response.status+').');
 return data;
}
async function generateOne(request){return generationRequest('/generation/one',request);}
async function saveGeneratedDraft(request){return generationRequest('/generation/drafts',request);}
async function listGeneratedDrafts(){
 const cfg=window.MBU_SOURCE_LIBRARY_STAGING||{};
 if(location.hostname!=='staging.srnastudytool.com'||!cfg.enabled)throw Error('Staging only.');
 const raw=cfg.generationApiUrl===undefined?'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/':cfg.generationApiUrl;
 if(!raw)throw Error('Staging generation backend disabled.');
 const u=new URL(raw);
 if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.hostname!=='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev')throw Error('Invalid staging generation backend.');
 const response=await fetch(u.origin+'/generation/drafts',{headers:{Authorization:'Bearer '+token()},credentials:'omit',cache:'no-store',redirect:'error'});
 const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.error||'Draft list unavailable ('+response.status+').');return data;
}
async function getGeneratedDraft(draftId){
 if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(draftId))throw Error('Invalid draft ID.');
 const cfg=window.MBU_SOURCE_LIBRARY_STAGING||{};
 if(location.hostname!=='staging.srnastudytool.com'||!cfg.enabled)throw Error('Staging only.');
 const raw=cfg.generationApiUrl===undefined?'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/':cfg.generationApiUrl;
 const u=new URL(raw);
 if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.hostname!=='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev')throw Error('Invalid staging generation backend.');
 const response=await fetch(u.origin+'/generation/drafts/'+draftId,{headers:{Authorization:'Bearer '+token()},credentials:'omit',cache:'no-store',redirect:'error'});
 const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.error||'Draft unavailable ('+response.status+').');return data;
}
async function revalidateGeneratedDraft(draftId){
 if(!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(draftId))throw Error('Invalid draft ID.');
 const cfg=window.MBU_SOURCE_LIBRARY_STAGING||{};
 if(location.hostname!=='staging.srnastudytool.com'||!cfg.enabled)throw Error('Staging only.');
 const raw=cfg.generationApiUrl===undefined?'https://srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev/':cfg.generationApiUrl;
 const u=new URL(raw);
 if(u.protocol!=='https:'||u.username||u.password||u.search||u.hash||u.pathname!=='/'||u.hostname!=='srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev')throw Error('Invalid staging generation backend.');
 const response=await fetch(u.origin+'/generation/drafts/'+draftId+'/revalidate',{method:'GET',headers:{Authorization:'Bearer '+token()},credentials:'omit',cache:'no-store',redirect:'error'});
 const data=await response.json().catch(()=>({}));if(!response.ok)throw Error(data.error||'Draft validation unavailable ('+response.status+').');return data;
}
window.MBUSourceMaterialStagingStorage=Object.freeze({save,list,file,download,reviewPdf,reviewQueue,verifiedReviewManifest,verifiedReviewPage,mobileReviewerAcceptance,remove,saveReviewDraft,loadReviewDraft,deleteReviewDraft,generationPreflight,checkGroqConnection,generateOne,saveGeneratedDraft,listGeneratedDrafts,getGeneratedDraft,revalidateGeneratedDraft});
})();
