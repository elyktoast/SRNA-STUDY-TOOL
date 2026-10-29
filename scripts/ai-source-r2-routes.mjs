import {R2_PART_BYTES} from './ai-source-r2-upload-config.mjs';
// R2 multipart endpoints. The caller supplies actorId from a verified Supabase
// session. Never trust actor IDs, object paths or bucket names in request bodies.
const UUID=/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const routes=new Set(['/source/uploads/r2/create','/source/uploads/r2/sign','/source/uploads/r2/parts','/source/uploads/r2/complete','/source/uploads/r2/abort']);
export function createR2UploadRoutes({authorizeAdmin,getOwnedIntent,controller,getSession,saveSession,markComplete,clearSession}){
 if(typeof authorizeAdmin!=='function'||typeof getOwnedIntent!=='function'||!controller||
  typeof getSession!=='function'||typeof saveSession!=='function'||typeof markComplete!=='function'||typeof clearSession!=='function')
  throw new TypeError('trusted R2 route adapters required');
 return async({path,actorId,body})=>{
  if(!routes.has(path))return {status:404,body:{error:'not found'}};
  if(typeof actorId!=='string'||!UUID.test(actorId))return {status:401,body:{error:'authentication required'}};
  if(await authorizeAdmin(actorId)!==true)return {status:403,body:{error:'access denied'}};
  if(!body||typeof body!=='object'||Array.isArray(body)||typeof body.uploadId!=='string'||!UUID.test(body.uploadId))
   return {status:400,body:{error:'invalid upload request'}};
  try{
   const intent=await getOwnedIntent({uploadId:body.uploadId,actorId});
   if(!intent||intent.status!=='uploading'||intent.storage_bucket!=='srna-private-textbooks')
    return {status:409,body:{error:'upload unavailable'}};
   const current=await getSession({uploadId:body.uploadId,actorId});
   if(path==='/source/uploads/r2/create'){
    if(current?.multipart_id)return {status:200,body:{multipartId:current.multipart_id,partBytes:R2_PART_BYTES}};
    const created=await controller.initiate(intent);
    const saved=await saveSession({uploadId:body.uploadId,actorId,multipartId:created.multipartId});
    if(!saved){await controller.abort(intent,{multipartId:created.multipartId});throw new Error('multipart session persistence failed');}
    return {status:200,body:created};
   }
   if(!current?.multipart_id||current.multipart_id!==body.multipartId)
    return {status:409,body:{error:'multipart session unavailable'}};
   if(path==='/source/uploads/r2/parts'){
    if(current.r2_completed_at)return {status:409,body:{error:'multipart already completed'}};
    return {status:200,body:await controller.listParts(intent,{multipartId:body.multipartId})};
   }
   if(path==='/source/uploads/r2/sign'){
    if(current.r2_completed_at)return {status:409,body:{error:'multipart already completed'}};
    const signed=await controller.signPart(intent,{multipartId:body.multipartId,partNumber:body.partNumber});
    return {status:200,body:signed};
   }
   if(path==='/source/uploads/r2/complete'){
    if(current.r2_completed_at)return {status:409,body:{error:'multipart already completed'}};
    const completed=await controller.complete(intent,{multipartId:body.multipartId,parts:body.parts});
    const marked=await markComplete({uploadId:body.uploadId,actorId,multipartId:body.multipartId});
    if(!marked)throw new Error('multipart completion state unavailable');
    return {status:200,body:completed};
   }
   if(path==='/source/uploads/r2/abort'){
    if(current.r2_completed_at)return {status:409,body:{error:'multipart already completed'}};
    await controller.abort(intent,{multipartId:body.multipartId});
    if(!await clearSession({uploadId:body.uploadId,actorId,multipartId:body.multipartId}))throw new Error('multipart session cleanup failed');
    return {status:200,body:{aborted:true}};
   }
   return {status:404,body:{error:'not found'}};
  }catch(error){
   if(/invalid/.test(error.message))return {status:400,body:{error:'invalid multipart request'}};
   return {status:500,body:{error:'R2 upload operation failed'}};
  }
 };
}
