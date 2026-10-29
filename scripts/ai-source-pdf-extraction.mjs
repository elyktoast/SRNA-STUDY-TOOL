export async function extractPdfPages(pdf){
 if(!pdf||!Number.isInteger(pdf.numPages)||pdf.numPages<1||typeof pdf.getPage!=='function')
  throw new TypeError('invalid PDF adapter');
 const pages=[];
 for(let n=1;n<=pdf.numPages;n++){
  const page=await pdf.getPage(n);
  const result=await page.getTextContent();
  if(!Array.isArray(result?.items)) throw new Error('invalid page text '+n);
  const text=result.items.map(x=>typeof x?.str==='string'?x.str:'').join(' ').trim();
  pages.push({physicalPage:n,text,needsOcr:text.length<20});
 }
 return {pages,ocrPages:pages.filter(p=>p.needsOcr).map(p=>p.physicalPage)};
}
