(()=>{'use strict';
const cfg=window.MBU_SUPABASE_CONFIG||{},SESSION='mbu_supabase_session_v1',BUCKET='source-materials';
function session(){try{return JSON.parse(localStorage.getItem(SESSION)||'null')||{}}catch{return{}}}
function userId(jwt){try{const p=jwt.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');return JSON.parse(atob(p.padEnd(Math.ceil(p.length/4)*4,'='))).sub||''}catch{return session().user?.id||''}}
function safeName(name){return String(name||'material').replace(/[^a-zA-Z0-9._-]+/g,'_').replace(/^_+|_+$/g,'').slice(-180)||'material'}
async function save(file){
 if(!file)throw Error('Choose a file first.');
 const s=session(),jwt=s.access_token||'',uid=userId(jwt);if(!jwt||!uid)throw Error('Sign in before saving source material.');
 if(!cfg.url||!cfg.publishableKey)throw Error('Source material storage is not configured.');
 const path=uid+'/'+Date.now()+'-'+safeName(file.name);
 const res=await fetch(cfg.url+'/storage/v1/object/'+BUCKET+'/'+path,{method:'POST',headers:{Authorization:'Bearer '+jwt,apikey:cfg.publishableKey,'Content-Type':file.type||'application/octet-stream','x-upsert':'false'},body:file});
 const data=await res.json().catch(()=>({}));if(!res.ok)throw Error(data.message||data.error||'Could not save source material.');
 return {path,name:file.name,size:file.size,type:file.type||'',savedAt:new Date().toISOString()}
}
async function request(path,opts={}){
 const s=session(),jwt=s.access_token||'';if(!jwt)throw Error('Sign in to view source materials.');if(!cfg.url||!cfg.publishableKey)throw Error('Source material storage is not configured.');
 const res=await fetch(cfg.url+'/storage/v1/'+path,{...opts,headers:{Authorization:'Bearer '+jwt,apikey:cfg.publishableKey,...(opts.headers||{})}});
 const data=await res.json().catch(()=>null);if(!res.ok)throw Error(data?.message||data?.error||'Source material request failed.');return data
}
async function list(){
 const s=session(),jwt=s.access_token||'',uid=userId(jwt);if(!jwt)return[];if(!uid)throw Error('Could not identify the signed-in account.');
 const rows=await request('object/list/'+BUCKET,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prefix:uid+'/',limit:100,offset:0,sortBy:{column:'created_at',order:'desc'}})});
 return (rows||[]).map(x=>({name:String(x.name||'').replace(/^\d+-/,''),objectName:x.name,path:uid+'/'+x.name,createdAt:x.created_at,size:Number(x.metadata?.size||0),type:x.metadata?.mimetype||''}))
}
async function file(path,name,type){
 const s=session(),jwt=s.access_token||'';if(!jwt)throw Error('Sign in to use source material.');if(!cfg.url||!cfg.publishableKey)throw Error('Source material storage is not configured.');const res=await fetch(cfg.url+'/storage/v1/object/authenticated/'+BUCKET+'/'+path,{headers:{Authorization:'Bearer '+jwt,apikey:cfg.publishableKey}});
 if(!res.ok)throw Error('Could not load source material.');const blob=await res.blob();return new File([blob],name||'source-material',{type:type||blob.type||'application/octet-stream'})
}
async function download(path,name){
 const s=session(),jwt=s.access_token||'';if(!jwt)throw Error('Sign in to download source material.');if(!cfg.url||!cfg.publishableKey)throw Error('Source material storage is not configured.');const res=await fetch(cfg.url+'/storage/v1/object/authenticated/'+BUCKET+'/'+path,{headers:{Authorization:'Bearer '+jwt,apikey:cfg.publishableKey}});
 if(!res.ok)throw Error('Could not download source material.');const blob=await res.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name||'source-material';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)
}
async function remove(path){await request('object/'+BUCKET+'/'+path,{method:'DELETE'});}
window.MBUSourceMaterialStorage=Object.freeze({save,list,file,download,remove});
})();