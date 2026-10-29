// Framework-neutral server endpoint. Mount behind HTTPS with a verified session resolver.
// Never pass privileged database credentials or service keys to the browser.
export function createSourceHttpHandler({workflow,getAuthenticatedActor,maxBytes=104857600}){
 if(typeof workflow?.upload!=='function'||typeof workflow?.process!=='function')
  throw new TypeError('source workflow required');
 if(typeof getAuthenticatedActor!=='function') throw new TypeError('session resolver required');
 if(!Number.isSafeInteger(maxBytes)||maxBytes<8) throw new RangeError('invalid size limit');
 return async function handle({method,path,headers={},body}){
  if(method!=='POST'||!['/source/upload','/source/process'].includes(path))
   return {status:404,body:{error:'not found'}};
  try{
   const actorId=await getAuthenticatedActor({headers});
   if(typeof actorId!=='string'||!actorId.trim())
    return {status:401,body:{error:'authentication required'}};
   return await execute({workflow,maxBytes,path,body,actorId});
  }catch(error){
   if(/access denied/i.test(error?.message??'')) return {status:403,body:{error:'forbidden'}};
   if(/invalid|PDF bytes required|title|signature|exceeds upload limit/i.test(error?.message??''))
    return {status:400,body:{error:'invalid request'}};
   // Do not expose SQL errors, storage paths, stack traces, or server configuration.
   return {status:500,body:{error:'source operation failed'}};
  }
 };
}

// Only trusted server transport code may supply actorId here.
export async function executeAuthenticatedSourceOperation({workflow,maxBytes=104857600,path,body,actorId}){
 if(typeof actorId!=='string'||!actorId.trim()) return {status:401,body:{error:'authentication required'}};
 try{return await execute({workflow,maxBytes,path,body,actorId})}
 catch(error){
  if(/access denied/i.test(error?.message??'')) return {status:403,body:{error:'forbidden'}};
  if(/invalid|PDF bytes required|title|signature|exceeds upload limit/i.test(error?.message??'')) return {status:400,body:{error:'invalid request'}};
  return {status:500,body:{error:'source operation failed'}};
 }
}
async function execute({workflow,maxBytes,path,body,actorId}){
   if(path==='/source/upload'){
    if(!(body?.bytes instanceof Uint8Array)||body.bytes.length>maxBytes)
     return {status:413,body:{error:'invalid PDF size'}};
    const result=await workflow.upload({actorId,bytes:body.bytes,title:body.title});
    return {status:201,body:{document:result}};
   }
   if(typeof body?.documentId!=='string'||!body.documentId.trim())
    return {status:400,body:{error:'document ID required'}};
   const result=await workflow.process({actorId,documentId:body.documentId});
   return {status:200,body:{result}};
}
