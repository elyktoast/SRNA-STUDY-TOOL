(()=>{'use strict';
const status=document.getElementById('status'),app=document.getElementById('app'),summary=document.getElementById('summary'),exportButton=document.getElementById('export');
let draft=null;
const textbook=document.getElementById('textbook'),saveButton=document.getElementById('save'),loadButton=document.getElementById('load');
function updateButtons(){exportButton.disabled=!draft;saveButton.disabled=!draft||!textbook.value;loadButton.disabled=!textbook.value;}
textbook.addEventListener('change',()=>{draft=null;summary.textContent='';updateButtons();});
function validate(payload){
 if(!payload||payload.schema_version!==2||!/^[a-f0-9]{64}$/.test(payload.review_fingerprint)||!Array.isArray(payload.decisions)||!payload.decisions.length||payload.decisions.length>1000)throw Error('Invalid or unsupported review draft');
 const choices=new Set(['Needs review','Chapter','Subsection','Reject']);
 for(let i=0;i<payload.decisions.length;i++){
  const d=payload.decisions[i];
  if(!d||d.group!==i+1||!choices.has(d.decision)||typeof d.notes!=='string'||d.notes.length>2000)throw Error('Invalid or out-of-order review decision at group '+(i+1));
 }
 return payload;
}
async function boot(){
 if(location.hostname!=='staging.srnastudytool.com'||!window.MBUSourceMaterialStagingStorage){status.textContent='This page is available only in staging.';return;}
 try{
  // The staging Worker checks the live Supabase user and explicit admin UID allowlist.
  const books=await window.MBUSourceMaterialStagingStorage.list();
  for(const book of books){const option=document.createElement('option');option.value=book.path;option.textContent=book.name;textbook.appendChild(option)}
  app.hidden=false;status.textContent='Staging admin access verified. Private drafts are unapproved.';
 }catch(e){status.textContent='Access denied: '+e.message;}
}
document.getElementById('decisions').addEventListener('change',async e=>{
 draft=null;updateButtons();summary.textContent='';
 const file=e.target.files?.[0];if(!file)return;
 if(file.size>250000){summary.textContent='Draft exceeds size limit.';return;}
 try{
  const data=validate(JSON.parse(await file.text()));draft=data;
  const counts={};for(const d of data.decisions)counts[d.decision]=(counts[d.decision]||0)+1;
  summary.textContent='Validated draft structure: '+data.decisions.length+' groups; '+Object.entries(counts).map(([k,v])=>k+': '+v).join(', ')+'. Fingerprint and group correspondence must still be checked against source candidates before approval.';
  updateButtons();
 }catch(e){summary.textContent='Rejected: '+e.message;}
});
document.getElementById('packet').addEventListener('change',e=>{
 const f=e.target.files?.[0];if(f)status.textContent='Selected local review packet: '+f.name+'. Open it locally to inspect headings; this page does not execute or upload HTML.';
});
saveButton.addEventListener('click',async()=>{
 if(!draft||!textbook.value)return;
 saveButton.disabled=true;
 try{const result=await window.MBUSourceMaterialStagingStorage.saveReviewDraft(textbook.value,draft);summary.textContent='Private review draft saved. Approved: '+String(result.approved)+'. Chapter assignments unchanged.'}
 catch(e){summary.textContent='Save failed: '+e.message}
 finally{updateButtons()}
});
loadButton.addEventListener('click',async()=>{
 if(!textbook.value)return;
 loadButton.disabled=true;
 try{draft=validate(await window.MBUSourceMaterialStagingStorage.loadReviewDraft(textbook.value));summary.textContent='Saved private draft loaded. Candidate fingerprint still requires independent verification before approval.'}
 catch(e){draft=null;summary.textContent='Load failed: '+e.message}
 finally{updateButtons()}
});
exportButton.addEventListener('click',()=>{
 if(!draft)return;
 const blob=new Blob([JSON.stringify(draft,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob);
 const a=document.createElement('a');a.href=url;a.download='chapter-review-validated-draft.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
});
boot();
})();
