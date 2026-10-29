import {uploadPdfToR2} from './ai-source-browser-r2.mjs';
import {MAX_TEXTBOOK_BYTES} from './ai-source-upload-constants.mjs';

// Call only from an authenticated admin UI. request() must use same-origin
// credentials and CSRF protections provided by the application.
export async function submitSourceTextbook({
 file,request,fetchPart,progress,signal,resumeUploadId
}){
 if(typeof request!=='function')throw new TypeError('authenticated request adapter required');
 if(!file||typeof file.name!=='string'||!file.name.trim()||file.name.trim().length>250)
  throw new Error('invalid PDF title');
 if(!Number.isSafeInteger(file.size)||file.size<8||file.size>MAX_TEXTBOOK_BYTES||file.type!=='application/pdf')
  throw new Error('invalid PDF file');
 if(signal?.aborted)throw new Error('upload canceled');
 let uploadId=resumeUploadId;
 if(uploadId!==undefined){
  if(typeof uploadId!=='string'||!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(uploadId))
   throw new Error('invalid resume upload ID');
 }else{
  const created=await request('/source/uploads/initiate',{
   title:file.name.trim(),fileBytes:file.size,mimeType:file.type
  });
  if(!created||typeof created.upload?.uploadId!=='string'||
     created.upload.fileBytes!==file.size||created.upload.status!=='pending')
   throw new Error('invalid initiated upload');
  uploadId=created.upload.uploadId;
  if(signal?.aborted)throw new Error('upload canceled');
  const started=await request('/source/uploads/start',{uploadId});
  if(started?.status!=='uploading')throw new Error('upload session could not start');
 }
 await uploadPdfToR2({file,uploadId,request,fetchPart,progress,signal});
 if(signal?.aborted)throw new Error('upload canceled');
 const verified=await request('/source/uploads/verify',{uploadId});
 if(verified?.result?.uploadId!==uploadId||!verified.result.document?.id)
  throw new Error('upload verification did not complete');
 return verified.result.document;
}
