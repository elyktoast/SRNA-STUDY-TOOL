// Node-only extraction. Install pdfjs-dist before enabling in upload worker.
// No network access or storage writes are performed by this module.
export async function extractPdfPages(bytes,{getDocument}={}){
  if(!(bytes instanceof Uint8Array)||bytes.length===0)
    throw new TypeError('PDF bytes must be a nonempty Uint8Array');
  const loader=getDocument??(await import('pdfjs-dist/legacy/build/pdf.mjs')).getDocument;
  const task=loader({data:new Uint8Array(bytes),useSystemFonts:true,disableFontFace:true});
  const pdf=await task.promise;
  const pages=[];
  try{
    for(let i=1;i<=pdf.numPages;i++){
      const page=await pdf.getPage(i);
      const content=await page.getTextContent();
      // Preserve line breaks when pdf.js marks a text item as ending a line.
      const text=content.items.map(item=>
        typeof item.str==='string'?item.str+(item.hasEOL?'\n':' '):''
      ).join('').trim();
      pages.push({physicalPage:i,text});
      page.cleanup?.();
    }
  }finally{
    await pdf.destroy();
  }
  return pages;
}
