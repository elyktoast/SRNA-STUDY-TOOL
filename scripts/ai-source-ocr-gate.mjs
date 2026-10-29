// OCR provider is injected by the server-side worker. Never discard scanned pages.
export async function resolveOcrPages(extraction,{ocrPage}={}){
 if(!Array.isArray(extraction?.pages)||!Array.isArray(extraction?.ocrPages))
   throw new TypeError('invalid PDF extraction');
 const pages=extraction.pages.map(p=>({...p}));
 if(extraction.ocrPages.length&&!ocrPage)
   throw new Error('OCR required for pages: '+extraction.ocrPages.join(','));
 const seen=new Set();
 for(const pageNumber of extraction.ocrPages){
   if(!Number.isInteger(pageNumber)||pageNumber<1||pageNumber>pages.length)
     throw new Error('invalid OCR page number');
   if(seen.has(pageNumber)) throw new Error('duplicate OCR page number');
   seen.add(pageNumber);
   if(pages[pageNumber-1].physicalPage!==pageNumber) throw new Error('invalid OCR page mapping');
   const replacement=await ocrPage(pageNumber);
   if(typeof replacement!=='string'||!replacement.trim())
     throw new Error('OCR produced no usable text on page '+pageNumber);
   pages[pageNumber-1]={...pages[pageNumber-1],text:replacement,needsOcr:false,extractionMethod:'ocr'};
 }
 return pages;
}
