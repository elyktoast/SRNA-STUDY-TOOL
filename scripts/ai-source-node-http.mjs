import {createServer} from 'node:http';
import {createSourceHttpHandler} from './ai-source-http-handler.mjs';

// Supply a trusted session resolver and backend workflow. No secrets in the browser.
export function createSourceNodeServer({workflow,getAuthenticatedActor,maxBytes=104857600}){
 const handle=createSourceHttpHandler({workflow,getAuthenticatedActor,maxBytes});
 return createServer(async(req,res)=>{
  const send=(status,body)=>{
   res.writeHead(status,{'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff'});
   res.end(JSON.stringify(body));
  };
  const path=new URL(req.url,'http://localhost').pathname;
  if(req.method!=='POST'||!['/source/upload','/source/process'].includes(path))
   return send(404,{error:'not found'});
  try{
   const parts=[];
   let size=0;
   const limit=path==='/source/upload'?maxBytes+4096:8192;
   for await(const part of req){
    size+=part.length;
    if(size>limit) return send(413,{error:'request too large'});
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
   const result=await handle({method:req.method,path,headers:req.headers,body});
   return send(result.status,result.body);
  }catch{
   if(!res.headersSent) send(500,{error:'source operation failed'});
   else res.destroy();
  }
 });
}
