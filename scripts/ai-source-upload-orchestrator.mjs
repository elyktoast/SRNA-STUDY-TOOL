import {uploadSourcePdfWithTus} from './ai-source-browser-tus.mjs';
import {MAX_TEXTBOOK_BYTES} from './ai-source-upload-constants.mjs';

// Call only from an authenticated admin UI. request() must use same-origin
// credentials and CSRF protections provided by the application.
export async function submitSourceTextbook({
 file,request,projectId,accessToken,userId,tus,progress,signal
}){
 if(typeof request!=='function')throw new TypeError('authenticated request adapter required');
 if(!file||typeof file.name!=='string'||!file.name.trim())throw new Error('PDF title required');
 if(!Number.isSafeInteger(file.size)||file.size<8||file.size>MAX_TEXTBOOK_BYTES||file.type!=='application/pdf')
  throw new Error('invalid PDF file');
 if(signal?.aborted)throw new Error('upload canceled');
 const created=await request('/source/uploads/initiate',{
  title:file.name,fileBytes:file.size,mimeType:file.type
 });
 if(!created||typeof created.upload?.uploadId!=='string'||
    created.upload.fileBytes!==file.size||created.upload.status!=='pending')
  throw new Error('invalid initiated upload');
 const uploadId=created.upload.uploadId;
 const started=await request('/source/uploads/start',{uploadId});
 if(started?.status!=='uploading')throw new Error('upload session could not start');
 await uploadSourcePdfWithTus({
  file,upload:{...created.upload,status:'uploading'},
  projectId,accessToken,userId,tus,progress,signal
 });
 if(signal?.aborted)throw new Error('upload canceled');
 const verified=await request('/source/uploads/verify',{uploadId});
 if(verified?.result?.uploadId!==uploadId||!verified.result.document?.id)
  throw new Error('upload verification did not complete');
 return verified.result.document;
}
