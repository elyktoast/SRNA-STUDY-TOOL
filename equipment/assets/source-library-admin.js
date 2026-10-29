// Admin-only Source Library upload panel. Host application supplies a verified Supabase session token.
export function mountSourceLibrary(root,{getAccessToken,apiBase='',onChanged}={}){
 if(!(root instanceof HTMLElement)) throw new TypeError('mount element required');
 if(typeof getAccessToken!=='function') throw new TypeError('session token provider required');
 const wrapper=document.createElement('section');
 wrapper.className='source-library-panel';
 const heading=document.createElement('h2');heading.textContent='Textbook Source Library';
 const description=document.createElement('p');description.textContent='Private admin workspace. Upload a PDF and start indexing after upload.';
 const form=document.createElement('form');
 const title=document.createElement('input');title.type='text';title.placeholder='Textbook title';title.required=true;title.maxLength=250;title.setAttribute('aria-label','Textbook title');
 const file=document.createElement('input');file.type='file';file.accept='.pdf,application/pdf';file.required=true;file.setAttribute('aria-label','PDF textbook');
 const upload=document.createElement('button');upload.type='submit';upload.textContent='Upload textbook';
 const process=document.createElement('button');process.type='button';process.textContent='Process uploaded PDF';process.disabled=true;
 const status=document.createElement('p');status.setAttribute('role','status');status.setAttribute('aria-live','polite');
 form.append(title,file,upload);
 wrapper.append(heading,description,form,process,status);root.replaceChildren(wrapper);
 let documentId=null,busy=false;
 function setBusy(value){busy=value;upload.disabled=value;process.disabled=value||!documentId;title.disabled=value;file.disabled=value}
 async function request(path,options){
  const token=await getAccessToken();
  if(typeof token!=='string'||!token.trim()) throw new Error('Sign in as an administrator before uploading.');
  const response=await fetch(apiBase+path,{...options,headers:{...options.headers,authorization:'Bearer '+token}});
  const payload=await response.json().catch(()=>({}));
  if(!response.ok) throw new Error(response.status===403?'Administrator access required.':payload.error||'Request failed');
  return payload;
 }
 form.addEventListener('submit',async event=>{
  event.preventDefault();if(busy)return;
  const selected=file.files?.[0];
  if(!selected||!selected.name.toLowerCase().endsWith('.pdf')){status.textContent='Choose a PDF textbook.';return}
  if(selected.size>104857600){status.textContent='PDF exceeds the 100 MB limit.';return}
  documentId=null;setBusy(true);status.textContent='Uploading PDF…';
  try{
   const payload=await request('/source/upload',{method:'POST',headers:{'content-type':'application/pdf','x-source-title':title.value.trim()},body:selected});
   if(typeof payload.document?.id!=='string') throw new Error('Upload returned no document ID');
   documentId=payload.document.id;status.textContent='Upload complete. Ready to process.';
   if(typeof onChanged==='function')onChanged();
  }catch(error){status.textContent=error.message||'Upload failed'}
  finally{setBusy(false)}
 });
 process.addEventListener('click',async()=>{
  if(busy||!documentId)return;
  setBusy(true);status.textContent='Processing textbook. Keep this page open…';
  try{
   const payload=await request('/source/process',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({documentId})});
   status.textContent=payload.result?.status==='ready'?'Textbook indexed successfully.':'Processing completed; verify document status.';
   if(typeof onChanged==='function')onChanged();
  }catch(error){status.textContent=error.message||'Processing failed'}
  finally{setBusy(false)}
 });
 return {destroy(){wrapper.remove()}};
}
