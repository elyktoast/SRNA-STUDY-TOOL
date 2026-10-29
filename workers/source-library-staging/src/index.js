// Dedicated staging-only Source Library API. Never bind a production bucket here.
const json=(value,status=200,headers={})=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json','cache-control':'no-store',...headers}});
const MAX_BYTES=20*1024*1024;
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function cors(origin){return {'access-control-allow-origin':origin,'access-control-allow-methods':'GET,POST,DELETE,OPTIONS','access-control-allow-headers':'authorization,content-type','access-control-max-age':'600','vary':'Origin'};}
function validKey(key,uid){return typeof key==='string'&&key.startsWith(uid+'/')&&key.length<=300&&/^[-a-zA-Z0-9_./]+$/.test(key)&&!key.includes('..')&&!key.includes('//');}
async function identity(request,env){
 const match=/^Bearer (.+)$/.exec(request.headers.get('authorization')||'');
 if(!match||!env.SUPABASE_URL||!env.SUPABASE_ANON_KEY||!env.ADMIN_USER_IDS)return null;
 const response=await fetch(env.SUPABASE_URL.replace(/\/$/,'')+'/auth/v1/user',{headers:{authorization:'Bearer '+match[1],apikey:env.SUPABASE_ANON_KEY}});
 if(!response.ok)return null;
 const user=await response.json();
 if(!uuid.test(user?.id||''))return null;
 const allowed=env.ADMIN_USER_IDS.split(',').map(x=>x.trim().toLowerCase());
 return allowed.includes(user.id.toLowerCase())?user.id:null;
}
export default {async fetch(request,env){
 const origin=request.headers.get('origin')||'';
 const allowed=env.ALLOWED_ORIGIN||'https://staging.srnastudytool.com';
 if(env.STAGING_ONLY!=='true'||!env.TEXTBOOKS||!env.SUPABASE_URL||!env.SUPABASE_ANON_KEY||!env.ADMIN_USER_IDS)return json({error:'Staging configuration incomplete'},503);
 if(origin!==allowed)return json({error:'Origin forbidden'},403);
 const h=cors(allowed);
 if(request.method==='OPTIONS')return new Response(null,{status:204,headers:h});
 const url=new URL(request.url);
 if(url.pathname==='/health'&&request.method==='GET')return json({ok:true,environment:'staging'},200,h);
 let uid;try{uid=await identity(request,env)}catch{return json({error:'Authentication unavailable'},503,h);}
 if(!uid)return json({error:'Forbidden'},403,h);
 if(url.pathname==='/materials'&&request.method==='GET'){
   const results=await env.TEXTBOOKS.list({prefix:uid+'/',limit:100});
   return json({items:results.objects.map(o=>({path:o.key,name:o.customMetadata?.name||o.key.split('/').pop(),size:o.size,createdAt:o.uploaded.toISOString(),type:'application/pdf'})),truncated:results.truncated},200,h);
 }
 if(url.pathname==='/materials'&&request.method==='POST'){
   const size=Number(request.headers.get('content-length')||0);
   if(size>MAX_BYTES)return json({error:'File too large'},413,h);
   if(request.headers.get('content-type')!=='application/pdf')return json({error:'PDF required'},415,h);
   const body=await request.arrayBuffer();
   if(body.byteLength<5||body.byteLength>MAX_BYTES)return json({error:'Invalid PDF size'},413,h);
   const bytes=new Uint8Array(body);
   if(String.fromCharCode(...bytes.slice(0,5))!=='%PDF-')return json({error:'Invalid PDF header'},415,h);
   const name=(request.headers.get('x-file-name')||'document.pdf').replace(/[^a-zA-Z0-9._-]/g,'_').slice(0,150);
   const key=uid+'/'+crypto.randomUUID()+'.pdf';
   await env.TEXTBOOKS.put(key,body,{httpMetadata:{contentType:'application/pdf'},customMetadata:{name}});
   return json({path:key,name,size:body.byteLength,type:'application/pdf',savedAt:new Date().toISOString()},201,h);
 }
 if(url.pathname==='/materials/item'&&(request.method==='GET'||request.method==='DELETE')){
   const key=url.searchParams.get('path');
   if(!validKey(key,uid))return json({error:'Invalid path'},400,h);
   if(request.method==='DELETE'){await env.TEXTBOOKS.delete(key);return json({ok:true},200,h);}
   const object=await env.TEXTBOOKS.get(key);
   if(!object)return json({error:'Not found'},404,h);
   return new Response(object.body,{headers:{...h,'content-type':'application/pdf','cache-control':'no-store','x-content-type-options':'nosniff','content-disposition':'attachment'}});
 }
 return json({error:'Not found'},404,h);
}};
