// Dedicated staging-only Source Library API. Never bind a production bucket here.
const json=(value,status=200,headers={})=>new Response(JSON.stringify(value),{status,headers:{'content-type':'application/json','cache-control':'no-store',...headers}});
const MAX_BYTES=20*1024*1024;
const PART_BYTES=8*1024*1024;
const MAX_LARGE_BYTES=300*1024*1024;
const uploadIdPattern=/^[a-zA-Z0-9_-]{10,200}$/;
const uuid=/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
function cors(origin){return {'access-control-allow-origin':origin,'access-control-allow-methods':'GET,POST,PUT,DELETE,OPTIONS','access-control-allow-headers':'authorization,content-type,x-file-name','access-control-max-age':'600','vary':'Origin'};}
function validKey(key,uid){return typeof key==='string'&&key.startsWith(uid+'/')&&key.length<=300&&/^[-a-zA-Z0-9_./]+$/.test(key)&&!key.includes('..')&&!key.includes('//');}
async function identity(request,env){
 const match=/^Bearer (.+)$/.exec(request.headers.get('authorization')||'');
 if(!match||!env.SUPABASE_URL||!env.SUPABASE_ANON_KEY||!env.ADMIN_USER_IDS)return null;
 const response=await fetch(env.SUPABASE_URL.replace(/\/$/,'')+'/auth/v1/user',{headers:{authorization:'Bearer '+match[1],apikey:env.SUPABASE_ANON_KEY}});
 if(!response.ok)return null;
 const user=await response.json();
 if(!uuid.test(user?.id||''))return null;
 if(user?.is_anonymous===true)return null;
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
   const reader=request.body?.getReader();if(!reader)return json({error:'Missing PDF body'},400,h);
   const chunks=[];let total=0;while(true){const {done,value}=await reader.read();if(done)break;total+=value.byteLength;if(total>MAX_BYTES){await reader.cancel();return json({error:'File too large'},413,h)}chunks.push(value)}
   const body=new Uint8Array(total);let offset=0;for(const chunk of chunks){body.set(chunk,offset);offset+=chunk.byteLength}
   if(body.byteLength<5||body.byteLength>MAX_BYTES)return json({error:'Invalid PDF size'},413,h);
   const bytes=new Uint8Array(body);
   if(String.fromCharCode(...bytes.slice(0,5))!=='%PDF-')return json({error:'Invalid PDF header'},415,h);
   const name=(request.headers.get('x-file-name')||'document.pdf').replace(/[^a-zA-Z0-9._-]/g,'_').slice(0,150);
   const key=uid+'/'+crypto.randomUUID()+'.pdf';
   await env.TEXTBOOKS.put(key,body,{httpMetadata:{contentType:'application/pdf'},customMetadata:{name}});
   return json({path:key,name,size:body.byteLength,type:'application/pdf',savedAt:new Date().toISOString()},201,h);
 }

 // Multipart uploads are isolated to the authenticated user's R2 prefix.
 if(url.pathname==='/materials/multipart/start'&&request.method==='POST'){
   let data;try{data=await request.json()}catch{return json({error:'Invalid JSON'},400,h)}
   const size=Number(data?.size);
   if(!Number.isSafeInteger(size)||size<=MAX_BYTES||size>MAX_LARGE_BYTES)return json({error:'Allowed size: over 20 MiB through 300 MiB'},413,h);
   const name=String(data?.name||'');
   if(!name.toLowerCase().endsWith('.pdf')||name.length>150)return json({error:'PDF filename required'},415,h);
   const safeName=name.replace(/[^a-zA-Z0-9._-]/g,'_');
   const key=uid+'/'+crypto.randomUUID()+'.pdf';
   const upload=await env.TEXTBOOKS.createMultipartUpload(key,{httpMetadata:{contentType:'application/pdf'},customMetadata:{name:safeName,size:String(size)}});
   return json({path:key,uploadId:upload.uploadId,partSize:PART_BYTES,maxSize:MAX_LARGE_BYTES},201,h);
 }
 if(url.pathname.startsWith('/materials/multipart/')&&['PUT','POST','DELETE'].includes(request.method)){
   const action=url.pathname.slice('/materials/multipart/'.length);
   if(!['part','complete','abort'].includes(action))return json({error:'Not found'},404,h);
   const key=url.searchParams.get('path');const uploadId=url.searchParams.get('uploadId');
   if(!validKey(key,uid)||!uploadIdPattern.test(uploadId||''))return json({error:'Invalid upload reference'},400,h);
   const upload=env.TEXTBOOKS.resumeMultipartUpload(key,uploadId);
   if(action==='part'&&request.method==='PUT'){
     const part=Number(url.searchParams.get('part'));
     if(!Number.isInteger(part)||part<1||part>40)return json({error:'Invalid part number'},400,h);
     const length=Number(request.headers.get('content-length')||0);
     if(length>PART_BYTES)return json({error:'Part too large'},413,h);
     const body=await request.arrayBuffer();
     if(!body.byteLength||body.byteLength>PART_BYTES)return json({error:'Invalid part size'},413,h);
     const result=await upload.uploadPart(part,body);
     return json({partNumber:result.partNumber,etag:result.etag},200,h);
   }
   if(action==='complete'&&request.method==='POST'){
     let data;try{data=await request.json()}catch{return json({error:'Invalid JSON'},400,h)}
     const parts=data?.parts;
     if(!Array.isArray(parts)||parts.length<3||parts.length>40||parts.some((p,i)=>p?.partNumber!==i+1||typeof p?.etag!=='string'||!p.etag))return json({error:'Invalid ordered parts'},400,h);
     await upload.complete(parts);
     return json({ok:true,path:key},200,h);
   }
   if(action==='abort'&&request.method==='DELETE'){await upload.abort();return json({ok:true},200,h)}
   return json({error:'Method not allowed'},405,h);
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
