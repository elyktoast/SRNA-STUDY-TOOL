(()=>{'use strict';
// Staging-only adapter. Not loaded by production unless explicitly included in a staging build.
const config=window.MBU_SOURCE_LIBRARY_STAGING||{};
const sessionKey='mbu_supabase_session_v1';
function settings(){const base=String(config.apiUrl||'').replace(/\/$/,'');if(location.hostname!=='staging.srnastudytool.com'||!config.enabled||!/^https:\/\//.test(base))throw Error('Staging Source Library is not configured.');return base;}
function token(){let s;try{s=JSON.parse(localStorage.getItem(sessionKey)||'null')}catch{}const jwt=s?.access_token;if(!jwt)throw Error('Sign in to the staging account first.');return jwt;}
async function call(path,options={}){
 const response=await fetch(settings()+path,{...options,headers:{Authorization:'Bearer '+token(),...(options.headers||{})}});
 if(!response.ok){const error=await response.json().catch(()=>null);throw Error(error?.error||'Staging storage request failed ('+response.status+').')}
 return response;
}
function key(path){if(typeof path!=='string'||!path||path.includes('..')||path.includes('\\')||path.startsWith('/'))throw Error('Invalid source material path.');return encodeURIComponent(path)}
async function save(file){
 if(!(file instanceof File))throw Error('Choose a PDF file.');
 if(file.type!=='application/pdf'||!file.name.toLowerCase().endsWith('.pdf'))throw Error('Only PDF files are supported in staging.');
 if(file.size>20*1024*1024)throw Error('Staging PDF limit is 20 MiB.');
 const response=await call('/materials',{method:'POST',headers:{'content-type':'application/pdf','x-file-name':file.name},body:file});
 return response.json();
}
async function list(){const response=await call('/materials');const data=await response.json();return (data.items||[]).map(x=>({...x,createdAt:x.createdAt||x.savedAt}));}
async function file(path,name){const response=await call('/materials/item?path='+key(path));const blob=await response.blob();return new File([blob],name||'source-material.pdf',{type:'application/pdf'});}
async function download(path,name){const response=await call('/materials/item?path='+key(path));const blob=await response.blob();const url=URL.createObjectURL(blob);try{const a=document.createElement('a');a.href=url;a.download=name||'source-material.pdf';a.click()}finally{setTimeout(()=>URL.revokeObjectURL(url),1000)}}
async function remove(path){await call('/materials/item?path='+key(path),{method:'DELETE'});}
window.MBUSourceMaterialStagingStorage=Object.freeze({save,list,file,download,remove});
})();
