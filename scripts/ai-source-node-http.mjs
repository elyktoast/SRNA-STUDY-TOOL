import {createServer} from 'node:http';
import {executeAuthenticatedSourceOperation} from './ai-source-http-handler.mjs';

// Supply a trusted session resolver and backend workflow. No secrets in the browser.
export function createSourceNodeServer({workflow,getAuthenticatedActor,maxBytes=104857600}){
 if(typeof getAuthenticatedActor!=='function') throw new TypeError('session resolver required');
 if(!Number.isSafeInteger(maxBytes)||maxBytes<8) throw new RangeError('invalid size limit');
 if(typeof workflow?.upload!=='function'||typeof workflow?.process!=='function') throw new TypeError('source workflow required');
 return createServer(async(req,res)=>{
  const send=(status,body)=>{
   res.writeHead(status,{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'});
   res.end(JSON.stringify(body));
  };
  let path;
  try{path=new URL(req.url,'http://localhost').pathname}
  catch{return send(400,{error:'invalid request path'})}
  if(!((req.method==='POST'&&['/source/upload','/source/process'].includes(path))||(req.method==='GET'&&['/source/documents','/source/detail'].includes(path))))
   return send(404,{error:'not found'});
  try{
   const actor=await getAuthenticatedActor({headers:req.headers});
   if(typeof actor!=='string'||!actor.trim()) return send(401,{error:'authentication required'});
   if(req.method==='GET'){
    const url=new URL(req.url,'http://localhost');
    const result=await executeAuthenticatedSourceOperation({workflow,maxBytes,path,body:{documentId:url.searchParams.get('id')},actorId:actor});
    return send(result.status,result.body);
   }
   if(path==='/source/upload'){
    if(req.headers['content-type']?.split(';')[0]?.trim()!=='application/pdf')
     return send(415,{error:'PDF required'});
    if(typeof req.headers['x-source-title']!=='string')
     return send(400,{error:'title required'});
   }
   const declaredLength=req.headers['content-length'];
   const limit=path==='/source/upload'?maxBytes:8192;
   if(typeof declaredLength==='string' && (!/^\d+$/.test(declaredLength) || !Number.isSafeInteger(Number(declaredLength))))
    return send(400,{error:'invalid content length'});
   if(typeof declaredLength==='string' && Number(declaredLength)>limit)
    return send(413,{error:'request too large'});
   const parts=[];
   let size=0;
   // Abort the stream immediately when the request exceeds the configured limit.
   for await(const part of req){
    size+=part.length;
    if(size>limit){
     // Drain without retaining further chunks; avoid buffering unbounded uploads.
     req.resume();
     return send(413,{error:'request too large'});
    }
    parts.push(part);
   }
   const raw=Buffer.concat(parts);
   let body;
   if(path==='/source/upload'){
    const title=req.headers['x-source-title'];
    if(typeof title!=='string') return send(400,{error:'title required'});
    body={title,bytes:new Uint8Array(raw)};
   }else{
    if(req.headers['content-type']?.split(';')[0]?.trim()!=='application/json')
     return send(415,{error:'JSON required'});
    try{body=JSON.parse(raw.toString('utf8'))}
    catch{return send(400,{error:'invalid JSON'})}
   }
   const result=await executeAuthenticatedSourceOperation({workflow,maxBytes,path,body,actorId:actor});
   return send(result.status,result.body);
  }catch{
   if(!res.headersSent) send(500,{error:'source operation failed'});
   else res.destroy();
  }
 });
}
