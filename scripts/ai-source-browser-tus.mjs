import {TUS_CHUNK_BYTES,MAX_TEXTBOOK_BYTES} from './ai-source-upload-constants.mjs';

// Browser transport only. Uses the signed-in user's access token, NEVER a service-role key.
// Requires separately reviewed Storage RLS that restricts uploads to owned active intents.
export async function uploadSourcePdfWithTus({
 file,upload,projectId,accessToken,userId,tus,progress=()=>{},signal
}){
 if(typeof tus?.Upload!=='function')throw new TypeError('TUS client required');
 if(!file||typeof file.size!=='number'||!Number.isSafeInteger(file.size)||
    file.size<8||file.size>MAX_TEXTBOOK_BYTES||file.type!=='application/pdf')
  throw new Error('invalid PDF file');
 if(!upload||upload.status!=='uploading'||upload.fileBytes!==file.size||typeof upload.uploadId!=='string'||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(upload.uploadId))
  throw new Error('upload intent does not match PDF');
 if(typeof projectId!=='string'||!/^[a-z0-9]{10,40}$/.test(projectId))
  throw new Error('invalid storage project');
 if(typeof accessToken!=='string'||!accessToken.trim())
  throw new Error('signed-in user token required');
 if(typeof userId!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(userId))
  throw new Error('authenticated user ID required');
 if(signal?.aborted)throw new Error('upload canceled');
 if(typeof progress!=='function')throw new TypeError('progress callback required');
 const objectName='documents/'+upload.uploadId+'.pdf';
 const endpoint='https://'+projectId+'.storage.supabase.co/storage/v1/upload/resumable';
 return new Promise((resolve,reject)=>{
  let settled=false;
  let task;
  let highestProgress=0;
  const finish=(error)=>{
   if(settled)return;
   settled=true;
   signal?.removeEventListener?.('abort',abort);
   if(error)reject(error);else resolve({uploadId:upload.uploadId,bytes:file.size});
  };
  const abort=()=>{Promise.resolve().then(()=>task?.abort?.()).catch(()=>{});finish(new Error('upload canceled'))};
  try{task=new tus.Upload(file,{
   endpoint,chunkSize:TUS_CHUNK_BYTES,uploadDataDuringCreation:true,
   fingerprint:async()=>['ai-source',projectId,userId,upload.uploadId,file.size].join(':'),
   retryDelays:[0,3000,5000,10000,20000],removeFingerprintOnSuccess:true,
   headers:{authorization:'Bearer '+accessToken}, // No x-upsert: replacement must remain forbidden.
   metadata:{bucketName:'ai-textbook-sources',objectName,contentType:'application/pdf'},
   onProgress:(done,total)=>{if(!settled&&total===file.size&&Number.isFinite(done)&&done>=highestProgress&&done<=total){highestProgress=done;try{progress({bytesUploaded:done,bytesTotal:total})}catch{/* UI callbacks must not abort a valid transfer */}}},
   onError:error=>finish(error),
   onSuccess:()=>finish()
  });}catch(error){finish(error);return}
  signal?.addEventListener?.('abort',abort,{once:true});
  if(signal?.aborted){abort();return}
  Promise.resolve().then(()=>task.findPreviousUploads()).then(previous=>{
   if(settled)return;
   if(previous?.length)task.resumeFromPreviousUpload(previous[0]);
   task.start();
  }).catch(error=>{if(!settled)finish(error)});
 });
}
