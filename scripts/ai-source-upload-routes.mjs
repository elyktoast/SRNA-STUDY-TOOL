import {createR2UploadRoutes} from './ai-source-r2-routes.mjs';
import {createResumableSourceIntent} from './ai-source-resumable-intent.mjs';
import {verifyCompletedTextbook} from './ai-source-upload-completion.mjs';

// Trusted caller supplies actorId from verified authentication, never the JSON body.
export function createSourceUploadRoutes({authorizeAdmin,createIntent,markUploading,verifyAdapters,r2}){
 if(typeof authorizeAdmin!=='function'||typeof createIntent!=='function'||typeof markUploading!=='function'||!verifyAdapters||typeof verifyAdapters!=='object'||
    ['claimVerification','inspectObject','readObject','completeVerifiedIntent','failVerification'].some(key=>typeof verifyAdapters[key]!=='function'))
  throw new TypeError('trusted upload dependencies required');
 const r2Routes=r2?createR2UploadRoutes({authorizeAdmin,...r2}):null;
 return async ({path,actorId,body})=>{
  if(path.startsWith('/source/uploads/r2/'))return r2Routes?await r2Routes({path,actorId,body}):{status:503,body:{error:'R2 not configured'}};
  if(!['/source/uploads/initiate','/source/uploads/start','/source/uploads/verify'].includes(path))
   return {status:404,body:{error:'not found'}};
  if(typeof actorId!=='string'||!actorId.trim()) return {status:401,body:{error:'authentication required'}};
  if(await authorizeAdmin(actorId)!==true) return {status:403,body:{error:'access denied'}};
  if(!body||typeof body!=='object'||Array.isArray(body)) return {status:400,body:{error:'JSON object required'}};
  try{
   if(path==='/source/uploads/initiate'){
    const upload=await createResumableSourceIntent({actorId,authorizeAdmin,title:body.title,fileBytes:body.fileBytes,mimeType:body.mimeType,createIntent});
    return {status:201,body:{upload}};
   }
   if(typeof body.uploadId!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(body.uploadId)) return {status:400,body:{error:'upload ID required'}};
   if(path==='/source/uploads/start'){
    const started=await markUploading({uploadId:body.uploadId,actorId});
    return started?{status:200,body:{status:'uploading'}}:{status:409,body:{error:'upload cannot start'}};
   }
   if(path==='/source/uploads/verify'){
    const result=await verifyCompletedTextbook({...verifyAdapters,actorId,uploadId:body.uploadId,authorizeAdmin});
    return {status:200,body:{result}};
   }
   return {status:404,body:{error:'not found'}};
  }catch(error){
   if(/invalid|PDF required|file size|title/.test(error.message))return {status:400,body:{error:'invalid upload request'}};
   if(/unavailable for verification/.test(error.message))return {status:409,body:{error:'upload not ready'}};
   return {status:500,body:{error:'upload operation failed'}};
  }
 };
}
