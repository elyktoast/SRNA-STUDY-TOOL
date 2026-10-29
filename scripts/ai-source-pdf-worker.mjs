import {loadSourcePdf} from './ai-source-pdf-loader.mjs';
import {resolveOcrPages} from './ai-source-ocr-gate.mjs';
import {processAdminSourceDocument} from './ai-source-admin-service.mjs';

// All callbacks must be supplied by trusted server code, never from user JSON.
export async function processAdminPdf({
 documentId,actorId,authorizeAdmin,readPrivatePdf,getDocument,ocrPage,
 saveChunks,setStatus
}){
 if(typeof readPrivatePdf!=='function') throw new TypeError('private PDF reader required');
 if(typeof getDocument!=='function') throw new TypeError('PDF loader required');
 return processAdminSourceDocument({
  documentId,actorId,authorizeAdmin,saveChunks,setStatus,
  loadPages:async id=>{
   const bytes=await readPrivatePdf(id);
   const extracted=await loadSourcePdf(bytes,{getDocument});
   return resolveOcrPages(extracted,{ocrPage});
  }
 });
}
