// pdfjs-dist is a server dependency. OCR remains a separate required provider for scanned pages.
export async function createSourcePdfJsProvider(){
 const pdfjs=await import('pdfjs-dist/legacy/build/pdf.mjs');
 if(typeof pdfjs.getDocument!=='function') throw new Error('PDF.js getDocument unavailable');
 return function getDocument({data}){
  if(!(data instanceof Uint8Array)) throw new TypeError('PDF data required');
  return pdfjs.getDocument({data,disableFontFace:true,useSystemFonts:true});
 };
}
