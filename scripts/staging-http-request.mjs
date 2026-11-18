// Node acceptance requests can legitimately spend >300s in independent review.
// Use a bounded HTTPS request without fetch's implicit header deadline. No retry.
import {request as httpsRequest} from 'node:https';
const hosts=new Set(['xqyasyambwdyhsjkftqu.supabase.co','srna-source-reviewer-gateway-staging.dalley-kyle.workers.dev','api.github.com']);
export function stagingFetch(url,options={},requestImpl=httpsRequest){
 const target=new URL(url);
 if(target.protocol!=='https:'||!hosts.has(target.hostname)||target.port||target.username||target.password)throw Error('Staging HTTPS destination rejected');
 const method=options.method||'GET';if(!['GET','POST'].includes(method))throw Error('Staging method rejected');
 return new Promise((resolve,reject)=>{
  const signal=options.signal||AbortSignal.timeout(480000);
  const req=requestImpl(target,{method,headers:options.headers,signal},res=>{
   let size=0;const chunks=[];
   res.on('data',chunk=>{size+=chunk.length;if(size>4194304){req.destroy(Error('Staging response exceeds limit'));return;}chunks.push(chunk);});
   res.on('error',reject);
   res.on('aborted',()=>reject(Error('Staging response interrupted')));
   res.on('end',()=>{
    if(res.statusCode>=300&&res.statusCode<400){reject(Error('Staging redirect rejected'));return;}
    const body=[204,205,304].includes(res.statusCode)?null:Buffer.concat(chunks);
    resolve(new Response(body,{status:res.statusCode,headers:res.headers}));
   });
  });
  req.on('error',reject);
  if(options.body!==undefined)req.write(options.body);
  req.end();
 });
}
