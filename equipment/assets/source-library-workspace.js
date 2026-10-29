// Hybrid admin workspace: compact library list and contextual document inspector.
// All document data must be supplied by an authenticated, admin-verified host.
import {mountSourceLibrary} from './source-library-admin.js';
export function mountSourceLibraryWorkspace(root,{getAccessToken,apiBase='',loadDocuments,loadDetails}={}){
 if(typeof getAccessToken!=='function') throw new TypeError('authenticated token provider required');
 const read=async path=>{
  const token=await getAccessToken();
  if(typeof token!=='string'||!token.trim())throw new Error('admin sign-in required');
  const response=await fetch(apiBase+path,{headers:{authorization:'Bearer '+token}});
  if(!response.ok)throw new Error('source library request failed');
  return response.json();
 };
 loadDocuments=loadDocuments|| (async()=> (await read('/source/documents')).documents);
 loadDetails=loadDetails|| (async id=>read('/source/detail?id='+encodeURIComponent(id)));

 const host=document.createElement('section');host.className='sl-workspace';
 host.innerHTML='<header class="sl-header"><div><h1>Textbook Source Library</h1><p>Private textbook sources for AI question generation</p></div><button type="button" class="sl-add">+ Add textbook</button></header><div class="sl-metrics" aria-label="Library totals"></div><div class="sl-controls"><input type="search" aria-label="Search textbooks" placeholder="Search textbooks…"><select aria-label="Filter by status"><option value="">All statuses</option><option value="ready">Ready</option><option value="processing">Processing</option><option value="failed">Needs attention</option></select></div><div class="sl-columns"><div class="sl-list" role="list" aria-label="Textbooks"></div><aside class="sl-details" aria-label="Textbook details"><p>Select a textbook to review its details.</p></aside></div><div class="sl-upload" hidden></div><p class="sl-feedback" role="status" aria-live="polite"></p>';
 root.replaceChildren(host);
 const list=host.querySelector('.sl-list'),details=host.querySelector('.sl-details'),metrics=host.querySelector('.sl-metrics'),search=host.querySelector('[type=search]'),filter=host.querySelector('select'),feedback=host.querySelector('.sl-feedback'),uploadHost=host.querySelector('.sl-upload');
 let documents=[],selected=null,uploadPanel=null,revision=0;
 const safeText=value=>String(value??'');
 const el=(tag,className,text)=>{const node=document.createElement(tag);if(className)node.className=className;if(text!==undefined)node.textContent=safeText(text);return node};
 const validStatus=value=>['ready','processing','failed','uploaded','extracting','indexing'].includes(value)?value:'unknown';
 function showDetails(doc){
  details.replaceChildren();
  const title=el('h2','',doc.title||'Untitled textbook');
  details.append(title,el('p','sl-muted','Status: '+validStatus(doc.processing_status)));
  const tabs=el('div','sl-tabs');
  for(const name of ['Overview','Pages & citations','AI retrieval']){
   const button=el('button','',name);button.type='button';
   button.addEventListener('click',async()=>{
    for(const child of tabs.children)child.setAttribute('aria-pressed',String(child===button));
    const content=details.querySelector('.sl-detail-content');content.replaceChildren(el('p','sl-muted','Loading…'));
    try{
     const record=await loadDetails(doc.id,name);
     if(selected!==doc.id)return;
     if(name==='Overview'){
      content.replaceChildren(el('p','','PDF pages: '+safeText(record.pageCount??'Not available')),el('p','','Indexed chunks: '+safeText(record.chunkCount??'Not available')));
     }else if(name==='Pages & citations'){
      const entries=Array.isArray(record.passages)?record.passages:[];
      content.replaceChildren(...(entries.length?entries.map(item=>{const section=el('article','sl-passage');section.append(el('strong','','PDF page '+safeText(item.pageStart??'?')+(item.printedPage?' · Printed '+safeText(item.printedPage):'')),el('p','',item.content||''));return section}):[el('p','sl-muted','No indexed passages available.')]));
     }else{
      content.replaceChildren(el('p','sl-muted','Course assignments and retrieval settings are read-only until admin endpoints are connected.'));
     }
    }catch{content.replaceChildren(el('p','sl-error','Unable to load document details.'))}
   });
   tabs.append(button);
  }
  details.append(tabs,el('div','sl-detail-content','Select a detail tab.'));
  tabs.firstChild.click();
 }
 function render(){
  const term=search.value.trim().toLowerCase(),state=filter.value;
  const shown=documents.filter(d=>(!state||validStatus(d.processing_status)===state)&&(!term||safeText(d.title).toLowerCase().includes(term)));
  metrics.replaceChildren(...[['Textbooks',documents.length],['Ready',documents.filter(d=>d.processing_status==='ready').length],['Processing',documents.filter(d=>['processing','extracting','indexing'].includes(d.processing_status)).length],['Needs attention',documents.filter(d=>d.processing_status==='failed').length]].map(([label,count])=>{const card=el('div','sl-metric');card.append(el('strong','',count),el('span','',label));return card}));
  list.replaceChildren();
  if(!shown.length)list.append(el('p','sl-muted','No textbooks match your filters.'));
  for(const doc of shown){
   const button=el('button','sl-item'+(doc.id===selected?' is-selected':''));button.type='button';button.setAttribute('role','listitem');
   button.append(el('strong','',doc.title||'Untitled textbook'),el('span','sl-status',validStatus(doc.processing_status)));
   button.addEventListener('click',()=>{selected=doc.id;render();showDetails(doc)});
   list.append(button);
  }
 }
 async function refresh(){
  const current=++revision;feedback.textContent='Loading private textbook library…';
  try{
   const rows=await loadDocuments();
   if(current!==revision)return;
   if(!Array.isArray(rows))throw Error('invalid document list');
   documents=rows.filter(d=>d&&typeof d.id==='string');
   feedback.textContent='';render();
  }catch{if(current===revision)feedback.textContent='Unable to load private textbook library.'}
 }
 search.addEventListener('input',render);filter.addEventListener('change',render);
 host.querySelector('.sl-add').addEventListener('click',()=>{
  if(uploadPanel){uploadPanel.destroy();uploadPanel=null;uploadHost.hidden=true;return}
  uploadHost.hidden=false;
  uploadPanel=mountSourceLibrary(uploadHost,{getAccessToken,apiBase});
 });
 void refresh();
 return {refresh,destroy(){revision++;host.remove()}};
}
