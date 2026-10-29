import {extractPdfPages} from './ai-source-pdf-extraction.mjs';

// Provide getDocument from the pinned PDF.js package in the trusted worker.
// Do not fetch arbitrary URLs or expose textbook bytes to a browser client.
export async function loadSourcePdf(pdfBytes,{getDocument}={}){
 if(!(pdfBytes instanceof Uint8Array)||pdfBytes.byteLength===0)
   throw new TypeError('nonempty PDF bytes required');
 if(typeof getDocument!=='function') throw new TypeError('PDF.js getDocument adapter required');
 const task=getDocument({data:new Uint8Array(pdfBytes)});
 if(!task||typeof task.promise?.then!=='function')
   throw new TypeError('invalid PDF.js loading task');
 let document;
 try{
   document=await task.promise;
   return await extractPdfPages(document);
 }finally{
   if(document&&typeof document.destroy==='function') await document.destroy();
   else if(typeof task.destroy==='function') await task.destroy();
 }
}
