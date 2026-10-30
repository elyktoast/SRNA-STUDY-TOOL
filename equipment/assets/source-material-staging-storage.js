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
async function remove(path){await call('/materials/item?path='+key(path),{method:'DELETE'});}
window.MBUSourceMaterialStagingStorage=Object.freeze({save,list,file,download,remove});
})();
